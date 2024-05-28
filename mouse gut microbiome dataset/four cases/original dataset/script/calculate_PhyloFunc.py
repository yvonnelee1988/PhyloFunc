from Bio import Phylo
import pandas as pd
import csv
taxon_name_change_table=pd.read_csv("taxon_change_name.csv", sep = ',')
# read tree file
tree = Phylo.read("16S-rRNA_ML-Tree_Rooted.NWK", "newick")
# name internal nodes
def assign_names(tree):
    node_count = 0
    for clade in tree.find_clades(order='postorder'):  
        if not clade.name:  
            node_count += 1
            clade.name = f"Node{node_count}"
    return tree
tree_with_names = assign_names(tree)
# rename the leaves nodes
def rename_leaf_nodes(node, rename_dict):
    if node.is_terminal():
        old_name = node.name
        if old_name in rename_dict["name"].tolist():
            new_name = rename_dict.loc[rename_dict['name'] == old_name, 'new_name'].iloc[0]
            node.name = new_name
        else:
            node.name='None'
    else:
        for child in node.clades:
            rename_leaf_nodes(child, rename_dict)
    return tree
       
# creat branches of tree with precedent, consequent, and weight
def generate_branches(clade):
    branches = []
    for child in clade.clades:
        if child.branch_length is not None:
            if clade.name:
                branches.append(clade.name) 
            else:
                branches.append(clade.clades[0].name)  
            if child.name:
                branches.append(child.name)  
            else:
                branches.append(child.clades[0].name)  
            branches.append(child.count_terminals())  
            branches.append(child.branch_length) 
    return branches
# creat nodes information
def collect_branches(clade):
    if clade.is_terminal():
        return 
    branches = generate_branches(clade)
    all_branches.append(branches)
    for child_clade in clade.clades:
        collect_branches(child_clade)
all_branches = []
rename_tree=rename_leaf_nodes(tree_with_names.root,taxon_name_change_table)  
collect_branches(rename_tree.root)   
with open("tree_rename.csv", mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Precedent", "consequent", "num_childnodes", "branch_length"])
    for branches in all_branches:
        if len(branches)==12:
            writer.writerow(branches[8:12])
        writer.writerow(branches[0:4])
        writer.writerow(branches[4:8])
branch=pd.read_csv("tree_rename.csv", sep = ',')
mice_data=pd.read_csv("preprocessed_data.csv", sep = ',')

#creat tax_composition,weighted_function_composition,function_composition
column_A = 'taxon'  
column_Bs = mice_data.columns.tolist()[2:]
tax_composition = pd.DataFrame()  
for column_B in column_Bs:
   grouped_sum = mice_data.groupby(column_A)[column_B].sum()
   total_sum = mice_data[column_B].sum()
   column_B_percentage = grouped_sum / total_sum
   tax_composition[column_B] = column_B_percentage
pd.DataFrame(tax_composition).to_csv('taxon_composition.csv', sep=',', encoding='utf-8', index=True)  

weighted_function_composition = pd.DataFrame() 
for column_B in column_Bs:
   grouped = mice_data.groupby(['taxon', 'COG_number'])[column_B].sum()
   total_sum = mice_data[column_B].sum()
   weighted_function_composition[column_B] = grouped / total_sum
pd.DataFrame(weighted_function_composition).to_csv('weighted_function_composition.csv', sep=',', encoding='utf-8', index=True) 

function_composition = pd.DataFrame() 
for column_B in column_Bs:
    grouped_sum = mice_data.groupby(['taxon', 'COG_number'])[column_B].sum()
    total_sum = mice_data.groupby(column_A)[column_B].sum()
    column_B_percentage = grouped_sum / total_sum
    function_composition[column_B] = column_B_percentage
pd.DataFrame(function_composition).to_csv('function_composition.csv', sep=',', encoding='utf-8', index=True)  

weighted_function_composition=pd.read_csv("weighted_function_composition.csv", sep = ',')
tree=rename_tree
def merge_weighted_function_composition_for_inner_nodes(clade):
    leaf_nodes = pd.DataFrame()
    if not clade.is_terminal(): 
        for sub_clade in clade.clades:
            if sub_clade.is_terminal() and sub_clade.name!="None":  
                inner_node_results = pd.DataFrame(weighted_function_composition[weighted_function_composition['taxon'] == sub_clade.name][:])
                inner_node_results['taxon'] = clade.name  
                leaf_nodes = pd.concat([leaf_nodes, inner_node_results])
            else:
                if sub_clade.name!="None":
                    leaf_nodes = pd.concat([leaf_nodes, merge_weighted_function_composition_for_inner_nodes(sub_clade)])   # 递归查找子节点的叶子节点集合
        if not leaf_nodes.empty:  
            leaf_nodes.columns = weighted_function_composition.columns
    return leaf_nodes

column_Bs = mice_data.columns.tolist()[2:]
extend_weighted_function_composition=pd.DataFrame()

for clade in tree.find_clades():
    if not clade.is_terminal():
        leaf_set = merge_weighted_function_composition_for_inner_nodes(clade)
        if not leaf_set.empty: 
            group=pd.DataFrame()
            for column_B in column_Bs:
               group[column_B] = leaf_set.groupby(['COG_number'])[column_B].sum()
            group.insert(0, 'taxon', clade.name)
            extend_weighted_function_composition = pd.concat([extend_weighted_function_composition, group])

extend_weighted_function_composition.reset_index(inplace=True)
cols = extend_weighted_function_composition.columns.tolist()
cols = cols[1:2] + cols[0:1] + cols[2:]
extend_weighted_function_composition = extend_weighted_function_composition[cols]           
weighted_function_composition_all=pd.concat([weighted_function_composition, extend_weighted_function_composition])
pd.DataFrame(extend_weighted_function_composition).to_csv('extend_weighted_function_composition.csv', sep=',', encoding='utf-8', index=False) 
pd.DataFrame(weighted_function_composition_all).to_csv('weighted_function_composition_merge_all_nodes.csv', sep=',', encoding='utf-8', index=False) 

#change weighted_function_composition to percentage
weighted_function_composition_percentage = pd.DataFrame()  
for column_B in column_Bs:
    grouped_sum = weighted_function_composition_all.groupby(['taxon', 'COG_number'])[column_B].sum()
    total_sum = weighted_function_composition_all.groupby(column_A)[column_B].sum()
    column_B_percentage = grouped_sum / total_sum
    weighted_function_composition_percentage[column_B] = column_B_percentage
pd.DataFrame(weighted_function_composition_percentage).to_csv('weighted_function_composition_percentage.csv', sep=',', encoding='utf-8', index=True)  
weighted_function_composition_percentage=pd.read_csv('weighted_function_composition_percentage.csv', sep=',')  
taxon_ID = weighted_function_composition_percentage['taxon'].drop_duplicates().reset_index(drop=True)
for i in range(len(taxon_ID)):
    for column_B in column_Bs:
        flag=weighted_function_composition_percentage["taxon"]==taxon_ID[i]
        if weighted_function_composition_percentage.loc[flag, column_B].isna().all():
            weighted_function_composition_percentage.loc[flag, column_B]=weighted_function_composition_percentage.loc[flag, column_B].fillna(1/len(weighted_function_composition_percentage.loc[flag, column_B]))
pd.DataFrame(weighted_function_composition_percentage).to_csv('weighted_function_composition_percentage_fillna.csv', sep=',', encoding='utf-8', index=False)  

taxon_composition=pd.read_csv("taxon_composition.csv", sep = ',')
def merge_taxon_composition_for_inner_nodes(clade):
    leaf_nodes = pd.DataFrame()
    if not clade.is_terminal():  
        for sub_clade in clade.clades:
            if sub_clade.is_terminal() and sub_clade.name!="None":  
                inner_node_results = pd.DataFrame(taxon_composition[taxon_composition['taxon'] == sub_clade.name][:])
                leaf_nodes = pd.concat([leaf_nodes,inner_node_results])
            else:
                if sub_clade.name!="None":
                    leaf_nodes = pd.concat([leaf_nodes, merge_taxon_composition_for_inner_nodes(sub_clade)])   # 递归查找子节点的叶子节点集合
        if not leaf_nodes.empty: 
            leaf_nodes.columns = taxon_composition.columns
            leaf_nodes['taxon'] = clade.name  
    return leaf_nodes

extend_taxon_composition=pd.DataFrame()
for clade in tree.find_clades():
    if not clade.is_terminal():
        leaf_set = merge_taxon_composition_for_inner_nodes(clade)
        if not leaf_set.empty: 
            group = leaf_set.sum().to_frame().transpose()
            group["taxon"]=clade.name
            extend_taxon_composition = pd.concat([extend_taxon_composition, group], ignore_index=True)
extend_taxon_composition.to_csv('extend_taxon_composition.csv', sep=',', encoding='utf-8', index=False) 
taxon_composition=pd.read_csv("taxon_composition.csv", sep = ',')
extend_taxon_composition_merge_all_nodes=pd.concat([taxon_composition, extend_taxon_composition])
pd.DataFrame(extend_taxon_composition_merge_all_nodes).to_csv('extend_taxon_composition_merge_all_nodes.csv', sep=',', encoding='utf-8', index=False) 

weighted_function_composition_percentage=pd.read_csv('weighted_function_composition_percentage_fillna.csv', sep=',')  
extend_taxon_composition_merge_all_nodes=pd.read_csv("extend_taxon_composition_merge_all_nodes.csv", sep = ',')
extend_taxon_composition_merge_all_nodes.iloc[:, [0,1]]
weight=pd.read_table('tree_rename.csv', sep = ',')
#caculation of Phylo_fun distance
dab_matrix_norm = pd.DataFrame()
taxon_len=len(weighted_function_composition_percentage.index)
column_len=len(weighted_function_composition_percentage.columns)
for a in range(2, column_len):
    Ga_function = weighted_function_composition_percentage.iloc[:, [0,1,a]]
    Ga_taxon = extend_taxon_composition_merge_all_nodes.iloc[:, [0,a-1]]
    for b in range(2, column_len):
        Gb_function = weighted_function_composition_percentage.iloc[:, b]
        Gb_taxon = extend_taxon_composition_merge_all_nodes.iloc[:, b-1]
        Gab_function = pd.concat([Ga_function, Gb_function], axis=1)
        Gab_taxon = pd.concat([Ga_taxon, Gb_taxon], axis=1)
        wUnifrac=0
        first_column_value = weighted_function_composition_percentage['taxon'].unique()
        for t in first_column_value:
            if t=='Node14':
                weight_taxon=1
            else:
                weight_taxon=weight.loc[weight['consequent']==t]['branch_length'].iloc[0]
            data_cog_tax=Gab_function[(Gab_function["taxon"]==t)]
            origin_data_norm = data_cog_tax.iloc[:,2:].apply(lambda x: x/sum(x), axis = 0).fillna(0) # normalized COG within each sample
            dab = 1 - sum(origin_data_norm.apply(lambda x: min(x), axis=1)) / sum(origin_data_norm.apply(lambda x: max(x), axis=1))
            a_abundance=Gab_taxon[(Gab_taxon["taxon"]==t)].iloc[0, 1] 
            b_abundance=Gab_taxon[(Gab_taxon["taxon"]==t)].iloc[0, 2] 
            wUnifrac=wUnifrac+dab*weight_taxon*a_abundance*b_abundance
        dab_matrix_norm.at[Gab_function.columns.values[2], Gab_function.columns.values[3]] = wUnifrac
        dab_matrix_norm.to_csv('PhyloFun_distance_mice.csv')
