# -*- coding: utf-8 -*-


import os
import os.path


def dirwalk(model, path, parent=None):
    for f in os.listdir(path):
        if not f.startswith('.'):
            is_dir = os.path.isdir(os.path.join(path, f))
            li = model.append(parent, [f, is_dir])
            if is_dir:
                dirwalk(model, os.path.join(path, f), li)


def sortfunc(model, iter_a, iter_b, user_data):
    data_a = model.get(iter_a, 0, 1)
    data_b = model.get(iter_b, 0, 1)

    if data_a[1] and not data_b[1]:
        # a is a directory; b is not
        return 1
    elif data_b[1] and not data_a[1]:
        # b is a directory; a is not
        return -1 
    else:
        # a and b are both either directories or files
        if data_a[0].lower() > data_b[0].lower():
            return -1
        else: 
            return 1
