import numpy as np
from criteria import criteria


class RelationManager:
    
    
    def __init__(self):
        
        self.all_criteria = criteria  # Full list of all criteria
        self.selected_criteria = []  # Currently selected criteria in GUI
        self.relation_matrix = None  # Will be resized based on selection
        self.n = len(criteria)
        self.relation_names = {}  # Store relation names for reference
        self._initialize_relations()
    def _initialize_relations(self):
        
        self.relation_matrix = np.zeros((self.n, self.n))
    
    def set_selected_criteria(self, selected_list):
        
        self.selected_criteria = selected_list
    
    def set_relation(self, criteria_i, criteria_j, weight):
        
        try:
            idx_i = self.all_criteria.index(criteria_i)
            idx_j = self.all_criteria.index(criteria_j)
            self.relation_matrix[idx_i][idx_j] = weight
        except ValueError as e:
            print(f"Criterion not found: {e}")
        
    def get_relation(self, criteria_i, criteria_j):
        
        try:
            idx_i = self.all_criteria.index(criteria_i)
            idx_j = self.all_criteria.index(criteria_j)
            return self.relation_matrix[idx_i][idx_j]
        except ValueError:
            return 0
    
    def get_full_relation_matrix(self):
        
        return self.relation_matrix.copy()
    
    def get_selected_relation_matrix(self):
        
        if not self.selected_criteria:
            return np.zeros((0, 0))
        
        indices = [self.all_criteria.index(c) for c in self.selected_criteria]
        submatrix = self.relation_matrix[np.ix_(indices, indices)]
        return submatrix.copy()
    
    def reset_relations(self):
        
        self.relation_matrix = np.zeros((self.n, self.n))
    
    def set_all_relations(self, relations_dict):
        
        self.reset_relations()
        for (crit_i, crit_j), weight in relations_dict.items():
            self.set_relation(crit_i, crit_j, weight)
