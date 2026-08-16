users = {}


def add_user(
    name,
    weights=None,
    dependencies=None,
    *,
    category_matrices=None,
    final_category_relations=None,
    category_scores=None,
    final_score=None,
    diagonal_values=None,
    criteria_by_category=None,
):
    """Add/update a supplier.

    Backwards compatible with the previous API (weights + dependencies).

    New workflow fields:
      - category_matrices: dict[str, list[list[float]]]
      - final_category_relations: list[list[float]]  (4x4 off-diagonal relations; diagonal ignored)
    """

    users[name] = {
        'weights': weights if weights is not None else {},
        'dependencies': dependencies if dependencies is not None else {},
        'category_matrices': category_matrices,
        'final_category_relations': final_category_relations,
        'category_scores': category_scores,
        'final_score': final_score,
        'diagonal_values': diagonal_values,
        'criteria_by_category': criteria_by_category,
    }


def get_users():
    
    return users


def get_user_weights(name):
    
    return users[name]['weights'] if name in users else {}


def get_user_dependencies(name):
    
    return users[name]['dependencies'] if name in users else {}


def clear_users():
    
    global users
    users = {}
