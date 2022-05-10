import numpy as np
import random
from copy import deepcopy
import colorama
from colorama import Fore, Style


class DataFrame:

    def __init__(self, file_path):
        assert file_path is not None, 'Please inform the file path'
        self.__read_csv(file_path)
        
        '''dict for each column type by column'''
        self.__init_col_types()
        '''list for each column index by name'''
        self.__init_col_to_index_dict()        
        self.shape = (len(self.values), len(self.columns))

        self.factorized_cols = dict()

    def __getitem__(self, key):
        key_type = type(key)
        if key_type == int:
            return self.values[key]
        elif key_type == str:
            j = self.__get_col_index_by_key(key)
            return np.array(
                [self.values[i][j] for i in range(self.shape[0])],
                dtype=self.column_types[j]
            )
        elif key_type == tuple:
            assert len(key) == 2, 'Invalid tuple size'
            if key[1] < 0:
                key = (key[0], self.shape[1] - key[1])
            new_values = []
            for row in self.values:
                new_values.append([x for i, x in enumerate(row) if i >= key[0] and i < key[1]])
            return new_values
        else:
            raise Exception('Invalid key type')

    def __init_col_to_index_dict(self):
        self.colum_to_index_dict = dict()
        for i, c in enumerate(self.columns):
            self.colum_to_index_dict[c] = i

    def __init_col_types(self):
        def get_value_type(v):
            try:
                int(v)
                return int
            except Exception:
                pass

            try:
                float(v)
                return float
            except Exception:
                pass

            return str

        self.column_types = []
        for j in range(len(self.columns)):
            type = get_value_type(self.values[0][j])
            self.column_types.append(type)
            for i in range(len(self.values)):
                self.values[i][j] = type(self.values[i][j])

    def __read_csv(self, file_path):
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        self.columns = lines[0].replace('\n', '').split(',')
        self.values = [l.replace('\n', '').split(',') for l in lines[1:]]

    def __get_col_index_by_key(self, key):
        key_type = type(key)
        if key_type == str:
            assert key in self.columns, 'Invalid key'
            return self.colum_to_index_dict[key]
        elif key_type == int:
            return key
        else:
            raise Exception('Invalid key type')

    def __continuous_split(self, key):
        col_i = self.__get_col_index_by_key(key)
        assert self.column_types[col_i] == float, 'This can only be done to continuous valued columns'

        values = self[self.columns[col_i]]
        median = np.median(values)
        median_str = '{:.2f}'.format(median)
    
        for i in range(self.shape[0]):
            self.values[i][col_i] = f'<={median_str}' if self.values[i][col_i] <= median else f'>{median_str}'
        self.column_types[col_i] = str

    def categorize_continuous_values(self):
        for i, t in enumerate(self.column_types):
            if t == float:
                self.__continuous_split(i)

    def factorize(self, key):
        col_i = self.__get_col_index_by_key(key)

        classes = set(self[self.columns[col_i]])
        class_dict = dict()
        inverse_class_dict = dict()
        for i, c in enumerate(classes):
            class_dict[c] = i
            inverse_class_dict[i] = c
        self.factorized_cols[self.columns[col_i]] = inverse_class_dict

        for i in range(self.shape[0]):
            self.values[i][col_i] = class_dict[self.values[i][col_i]]
        self.column_types[col_i] = int

    def train_test_split(self, X_indexes, y_class=-1, perc=.25):
        split_index = int(self.shape[0] * (1 - perc))
        shuffled_data = deepcopy(self.values)
        random.shuffle(shuffled_data)
        
        train, test = shuffled_data[:split_index], shuffled_data[split_index:]
        
        X_train = [x[X_indexes[0]:X_indexes[1]] for x in train]
        X_test = [x[X_indexes[0]:X_indexes[1]] for x in test]

        y_train = [x[y_class] for x in train]
        y_test = [x[y_class] for x in test]

        return X_train, X_test, y_train, y_test

    def get_values_by_cols(self, cols):
        return [[a for i, a in enumerate(x) if i in cols] for x in self.values]
    

class Node:

    def __init__(self, X, y, col_names, depth=0, parent=None):
        assert len(X) == len(y)
        if parent is None:
            assert len(X) > 0 and len(y) > 0
        #if len(X) > 0:
            #assert len(X[0]) == len(col_names)

        self.X, self.y = deepcopy(X), deepcopy(y)
        self.col_names = deepcopy(col_names)
        self.X_shape = (len(X), len(X[0]))
        self.depth = depth
        self.parent = parent

        self.is_leaf = self.__decide_if_leaf()
        if not self.is_leaf:
            self.__generate_children()

    def __call__(self, x):
        return self.predict(x)

    def predict(self, x):
        x = deepcopy(x)
        if self.is_leaf:
            return self.leaf_value
        else:
            deciding_col_value = x[self.deciding_col]
            del x[self.deciding_col]

            if deciding_col_value in self.children.keys():
                return self.children[deciding_col_value].predict(x)
            else:
                return self.children[random.choice(list(self.children.keys()))].predict(x)

    def most_common_y(self):
        count_dict = dict()
        for y_i in self.y:
            if y_i not in count_dict.keys():
                count_dict[y_i] = 1
            else:
                count_dict[y_i] += 1

        biggest_count = -1
        most_common_y = -1
        for y, count in count_dict.items():
            if count > biggest_count:
                biggest_count = count
                most_common_y = y
        return most_common_y, biggest_count

    def __get_column_values(self, col):
        assert col >= 0 and col < len(self.X[0]), 'Invalid key value'
        return [self.X[i][col] for i in range(len(self.X))]

    def __decide_if_leaf(self):
        if len(self.y) == 0:
            self.leaf_value, self.leaf_counter = self.parent.most_common_y()
            return True
        elif all([i == self.y[0] for i in self.y]):
            self.leaf_value = self.y[0]
            self.leaf_counter = len(self.y)
            return True
        elif self.X_shape[1] == 0:
            self.leaf_value, self.leaf_counter = self.parent.most_common_y()
            return True
        
        return False

    def __attribute_entropy(self, col):
        value_counter = dict()
        col_values = self.__get_column_values(col)
        for v in col_values:
            if v not in value_counter.keys():
                value_counter[v] = 1
            else:
                value_counter[v] += 1

        col_size = len(col_values)
        for k in value_counter.keys():
            value_counter[k] /= col_size

        return sum([(-1) * p * np.log2(p) for _, p in value_counter.items()])

    def __decide_most_important_attribute(self):
        assert self.X_shape[0] > 0
        
        highest_entropy = self.__attribute_entropy(0)
        highest_entropy_col = 0
        for j in range(1, self.X_shape[1]):
            tmp_entropy = self.__attribute_entropy(j)
            if tmp_entropy > highest_entropy:
                highest_entropy = tmp_entropy
                highest_entropy_col = j
        
        self.deciding_col = highest_entropy_col

    def __get_dropped_col_dataset(self, X, col):
        for x in X:
            del x[col]
        return X

    def __split_dataset_by_classes(self, X, y, deciding_col):
        classes = set(self.__get_column_values(deciding_col))
        class_to_dataset = dict()
        for c in classes:
            new_X, new_y = zip(*[(x, y_i,) for x, y_i in zip(X, y) if x[deciding_col] == c])
            class_to_dataset[c] = (new_X, new_y,)
        return class_to_dataset

    def __generate_children(self):
        self.__decide_most_important_attribute()
        self.children = dict()

        new_col_names = [c for i, c in enumerate(self.col_names) if i != self.deciding_col]

        class_to_dataset = self.__split_dataset_by_classes(self.X, self.y, self.deciding_col)
        for k, (new_X, new_y) in class_to_dataset.items():
            new_X = self.__get_dropped_col_dataset(new_X, self.deciding_col)
            self.children[k] = Node(new_X, new_y, new_col_names, self.depth+1, self)

    def print(self, inverser):
        if self.is_leaf:
            print(Fore.CYAN + f'{inverser[self.leaf_value]} ({self.leaf_counter})')
            return

        tabs = ''
        for _ in range(self.depth * 2):
            tabs += '    '
        
        attribute = self.col_names[self.deciding_col]
        print(Fore.WHITE + f'{tabs}<{attribute}>')
        
        for k, child in self.children.items():
            print(Fore.MAGENTA + f'{tabs}    {k}:', end=('\n' if not child.is_leaf else ' '))
            child.print(inverser)


class DecisionTree:

    def __init__(self, X, y, columns, inverse_class_dict):
        self.inverse_class_dict = inverse_class_dict
        self.root = Node(X, y, columns)

    def __call__(self, x):
        return self.predict(x)

    def predict(self, x):
        prediction = self.root(x)
        return self.inverse_class_dict[prediction]
    
    def evaluate(self, X, y):
        res = 0
        for x, y_i in zip(X, y):
            res += int(self(x) == self.inverse_class_dict[y_i])
        return res / len(y)

    def print(self):
        self.root.print(self.inverse_class_dict)
        print(Style.RESET_ALL)
        
        
if __name__ == '__main__':
    df = DataFrame(file_path='datasets/iris.csv')
    df.factorize('class')
    df.categorize_continuous_values()
    
    X_train, X_test, y_train, y_test = df.train_test_split((1, -1), perc=.25)

    inverser = df.factorized_cols['class']
    cols = df.columns[1:-1]
    dt = DecisionTree(X_train, y_train, cols, inverser)
    dt.print()
    
    print(f'Evaluation: {dt.evaluate(X_test, y_test) * 100:.2f}%')