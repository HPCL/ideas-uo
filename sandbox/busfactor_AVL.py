import sys, os, getpass, warnings
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.append(os.path.join(os.getcwd(), "..", "src"))
from patterns.visualizer import Visualizer
'''
-------------------------------------------------------------------------------
HELPER FUNCTIONS

csv_to_dict(file_name): takes a csv file as argument, returns a list

dict_sort(items): takes a list and returns dictionary of count and author

total_files(list): takes a list and returns the total files in a project

sort_from_list(items) : takes a list returned from csv_to_dict and returns a dictionary to be inputted to BF alg

busFactorCalcmin(num_file, data, metric, project_name = "Undefined"): num_file -> called from total_files data-> 
called from sort_from_list metric ->string of metric using - for output to keep track of what is being computed
 project_name -> string of project name for output
-------------------------------------------------------------------------------
'''
## Base class for AVL tree

class TreeNode(object):
    def __init__(self, key):
        self.key = key
        self.left = None
        self.right = None
        self.height = 1

## code adopted from https://www.programiz.com/dsa/avl-tree

class AVLTree(object):
    # Function to insert a node

    def insert_node(self, root, key):
        # Find the correct location and insert the node
        if not root:
            return TreeNode(key)
        elif key < root.key:
            root.left = self.insert_node(root.left, key)
        else:
            root.right = self.insert_node(root.right, key)

        root.height = 1 + max(self.getHeight(root.left),
                              self.getHeight(root.right))
        
        # Update the balance factor and balance the tree
        balanceFactor = self.getBalance(root)
        if balanceFactor > 1:
            if key < root.left.key:
                return self.rightRotate(root)
            else:
                root.left = self.leftRotate(root.left)
                return self.rightRotate(root)

        if balanceFactor < -1:
            if key > root.right.key:
                return self.leftRotate(root)
            else:
                root.right = self.rightRotate(root.right)
                return self.leftRotate(root)

        return root

    # Function to delete a node

    def delete_node(self, root, key):
        # Find the node to be deleted and remove it
        if not root:
            return root
        elif key < root.key:
            root.left = self.delete_node(root.left, key)
        elif key > root.key:
            root.right = self.delete_node(root.right, key)
        else:
            if root.left is None:
                temp = root.right
                root = None
                return temp
            elif root.right is None:
                temp = root.left
                root = None
                return temp
            temp = self.getMinValueNode(root.right)
            root.key = temp.key
            root.right = self.delete_node(root.right,
                                          temp.key)
        if root is None:
            return root

        # Update the balance factor of nodes
        root.height = 1 + max(self.getHeight(root.left),
                              self.getHeight(root.right))
        balanceFactor = self.getBalance(root)

        # Balance the tree
        if balanceFactor > 1:
            if self.getBalance(root.left) >= 0:
                return self.rightRotate(root)
            else:
                root.left = self.leftRotate(root.left)
                return self.rightRotate(root)
        if balanceFactor < -1:
            if self.getBalance(root.right) <= 0:
                return self.leftRotate(root)
            else:
                root.right = self.rightRotate(root.right)
                return self.leftRotate(root)
        return root

    # Function to perform left rotation
    def leftRotate(self, z):
        y = z.right
        T2 = y.left
        y.left = z
        z.right = T2
        z.height = 1 + max(self.getHeight(z.left),
                           self.getHeight(z.right))
        y.height = 1 + max(self.getHeight(y.left),
                           self.getHeight(y.right))
        return y

    # Function to perform right rotation
    def rightRotate(self, z):
        y = z.left
        T3 = y.right
        y.right = z
        z.left = T3
        z.height = 1 + max(self.getHeight(z.left),
                           self.getHeight(z.right))
        y.height = 1 + max(self.getHeight(y.left),
                           self.getHeight(y.right))
        return y

    # Get the height of the node
    def getHeight(self, root):
        if not root:
            return 0
        return root.height

    # Get balance factore of the node
    def getBalance(self, root):
        if not root:
            return 0
        return self.getHeight(root.left) - self.getHeight(root.right)

    def getMinValueNode(self, root):
        if root is None or root.left is None:
            return root
        return self.getMinValueNode(root.left)

    def preOrder(self, root):
        if not root:
            return
        print("{0} ".format(root.key), end="")
        self.preOrder(root.left)
        self.preOrder(root.right)

    # Print the tree
    def printTree(self, currPtr, indent, last):
        if currPtr != None:
            print(indent)
            if last:
                print("R----")
                indent += "     "
            else:
                print("L----")
                indent += "|    "
            print(currPtr.key)
            self.printTree(currPtr.left, indent, False)
            self.printTree(currPtr.right, indent, True)

def csv_to_dict(file_name):
    auth_list = []
    with open(file_name, "r") as file:
        for line in file:
            auth_list.append(line.split(','))
    return(auth_list)

def total_files(items):
    return len(items) - 1

def sort_from_list(items):
    items = items[1::]
    ret = {}
    for i in items:
        if i[1] not in ret:
            ret[i[1]] = 1
        else:
            ret[i[1]] += 1    
    return ret

def busFactorCalcmin(num_file, data, metric, project_name = "Undefined"):
    busfactor = 0
    count = 0
    # puts all of the numerical data in own list
    data_list = []
    for i in data:
        data_list.append(data[i])
    
    # initialize AVL tree
    t = AVLTree()
    root = None
    for i in data:
        root = t.insert_node(None, data[i])
  
    # compute BF
    runtime = 0
    while count < (num_file / 2):
        minNode = min(data_list)
        count += minNode
        t.delete_node(root, minNode)
        data_list.remove(minNode)
        
        busfactor += 1
        runtime += 1
        
    return [busfactor, metric, project_name]
'''
-------------------------------------------------------------------------------
BUS FACTOR CALCULATION

Calculates for a specified nymber of years defined in years

need to define years in a list

need to define project as a string

at the moment does not return anything, just prints a bunch of information
-------------------------------------------------------------------------------
'''

def calc_avl_bf(years, project_name):
    project = f"{project_name}"
    vis = Visualizer(project_name=project)
    vis.get_data()
    results_use = []
    for i in years:
        the_year = i
        yr_df = vis.commit_data[vis.commit_data["year"] == the_year]

        print(f"For the year {the_year} ...................")

        removed = vis.remove_external()
        vis.hide_names = False
        if not ("unique_author" in yr_df.columns):
            vis.set_unique_authors()

        """ vis.commit_data columns: 
        ['sha', 'branch', 'datetime', 'author', 'email', 'message', 'filepath',
            'diff', 'year', 'month', 'day', 'doy', 'dow', 'diff_summary',
            'locc-basic', 'locc', 'locc-', 'locc+', 'change-size-cos',
            'unique_author']
        """

        # Create author df containing just filenames
        author_df = yr_df[["filepath", "unique_author"]].reset_index().copy()
        author_df["commit_counts"] = 1

        # Count commits per author per file
        commits = author_df.groupby(["filepath", "unique_author"]).sum().reset_index()

        commits["total_commits"] = commits.groupby("filepath")["commit_counts"].transform("sum")
        commits.reset_index()

        # Compute a simple authorship metric based on commits
        commits["degree_commits"] = commits["commit_counts"] / commits["total_commits"]
        # print("\n>>> Degree of authorship based on commits:")
        # #print(commits.sort_values(by=["degree_commits"], ascending=False))
        # print("\n>>> Authors with DOA>0.75 per file:")
        doa_commits_df = (
            commits[commits["degree_commits"] >= 0.75]
            .groupby("filepath")
            .agg({"unique_author": ",".join})
            .sort_values(by=["unique_author"], ascending=False)
        )
        doa_commits_df.reset_index()

        # Next, compute a simple authorship metric based on lines of code and cos difference
        author_df = (
            vis.commit_data[["filepath", "unique_author", "locc-basic", "change-size-cos"]]
            .reset_index()
            .copy()
        )

        # Accumulate changes per author per file
        locc_counts = (
            author_df.groupby(["filepath", "unique_author"])
            .agg({"locc-basic": "sum", "change-size-cos": "sum"})
            .reset_index()
        )

        # Normalize changes per author per file (make them relative to totals per file)
        locc_counts["total_locc"] = locc_counts.groupby("filepath")["locc-basic"].transform(
            "sum"
        )
        locc_counts["degree_locc"] = locc_counts["locc-basic"] / locc_counts["total_locc"]

        locc_counts["total_cosdiff"] = locc_counts.groupby("filepath")[
            "change-size-cos"
        ].transform("sum")
        locc_counts["degree_cosdiff"] = (
            locc_counts["change-size-cos"] / locc_counts["total_cosdiff"]
        )
        # print("\n>>> Changes per file per author (normalized)\n ")
        # print("\n>>> Changes per file per author (normalized)\n", locc_counts)

        doa_df = (
            commits.merge(locc_counts, on=["filepath", "unique_author"])
            .reset_index()
            .drop(["index"], axis=1)
        )

        # BUS FACTOR: Commits
        print("Computing Bus Factor for commits...")
        commit_df = doa_df[["unique_author", "degree_commits"]]
        commit_df = commit_df[commit_df.degree_commits >= .75]      
        #commits[commits["degree_commits"] >= 0.75]
        len(commit_df)
        commit_df.columns[1]
        commit_df.to_csv(f'{project}-{commit_df.columns[1]}.csv')

        csv_commit_new = csv_to_dict(f'{project}-{commit_df.columns[1]}.csv')

        busFactorCalcmin(total_files(csv_commit_new), sort_from_list(csv_commit_new), "commits", project_name = f"{project}")
        results_use.append(busFactorCalcmin(total_files(csv_commit_new), sort_from_list(csv_commit_new), "commits", project_name = f"{project}"))
        print("BF: ", busFactorCalcmin(total_files(csv_commit_new), sort_from_list(csv_commit_new), "commits", project_name = f"{project}")[0])
        print("DONE FOR COMMITS...")
        print()

        # BUS FACTOR: LOCC
        print("Computing Bus Factor for locc...")
        locc_df = doa_df[["unique_author", "degree_locc"]]
        locc_df = locc_df[locc_df.degree_locc >= .75]      

        locc_df.columns[1]
        locc_df.to_csv(f'{project}-{locc_df.columns[1]}.csv')

        csv_locc_new = csv_to_dict(f'{project}-{locc_df.columns[1]}.csv')
        busFactorCalcmin(total_files(csv_locc_new), sort_from_list(csv_locc_new), "locc", project_name = f"{project}")
        print("BF: ", busFactorCalcmin(total_files(csv_locc_new), sort_from_list(csv_locc_new), "locc", project_name = f"{project}")[0])
        results_use.append(busFactorCalcmin(total_files(csv_locc_new), sort_from_list(csv_locc_new), "locc", project_name = f"{project}"))
        print("DONE FOR LOCC...")
        print()

        # BUS FACTOR: COS
        print("Computing Bus Factor for cos...")
        cos_df = doa_df[["unique_author", "degree_cosdiff"]]
        
        cos_df = cos_df[cos_df.degree_cosdiff >= .75]      
        #commits[commits["degree_commits"] >= 0.75]
        len(cos_df)
        cos_df.columns[1]
        cos_df.to_csv(f'{project}-{cos_df.columns[1]}.csv')

        csv_cos_new = csv_to_dict(f'{project}-{cos_df.columns[1]}.csv')
        busFactorCalcmin(total_files(csv_cos_new), sort_from_list(csv_cos_new), "cos", project_name = f"{project}")
        results_use.append(busFactorCalcmin(total_files(csv_cos_new), sort_from_list(csv_cos_new), "cos", project_name = f"{project}"))
        print("BF: ", busFactorCalcmin(total_files(csv_cos_new), sort_from_list(csv_cos_new), "cos", project_name = f"{project}")[0])
        print("DONE FOR COS... ")

    print()
    print("RESULTS TOGETHER")
    for j in results_use:
        print(j)
