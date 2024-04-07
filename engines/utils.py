# -*- coding: utf-8 -*-


def use_item(current_index, skip, take):
    """
    Determines whether an item at a given index should be used based on the skip and
    take parameters.

    Parameters:
    current_index (int): The index of the current item.
    skip (int): The number of items to skip.
    take (int): The number of items to take after skipping. If -1, takes all items.

    Returns:
    bool: True if the item should be used, False otherwise.

    The function returns False if the current index is less than the number of items to skip or
    if the current index is greater than or
    equal to the sum of the skip and take parameters (unless take is -1).
    Otherwise, it returns True.
    """
    if skip > 0 and current_index < skip:
        return False

    if take != -1 and current_index >= (skip + take):
        return False

    return True
