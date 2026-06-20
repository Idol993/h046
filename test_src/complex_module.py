import os
import sys
import json
import re
import time
import math
import random
import datetime
import collections
import itertools
import functools
import pathlib
import shutil
import tempfile
import glob
import hashlib
import base64
import urllib
import http
import socket


def very_complex_function(x, y, z):
    if x > 10:
        if y > 20:
            if z > 30:
                for i in range(100):
                    for j in range(50):
                        while True:
                            if i + j > 1000:
                                break
                            elif i * j > 500:
                                if x % 2 == 0:
                                    if y % 3 == 0:
                                        if z % 5 == 0:
                                            for k in range(10):
                                                if k > 5:
                                                    pass
                                                elif k < 2:
                                                    pass
                                                else:
                                                    pass
                            else:
                                pass
                    else:
                        pass
            else:
                pass
        elif y < 5:
            if z < 10:
                pass
            else:
                for i in range(10):
                    if i > 5:
                        if x < 0:
                            pass
        else:
            pass
    elif x < 0:
        if y < 0:
            if z < 0:
                while x < 100:
                    x += 1
                    if x % 2 == 0 and y % 3 == 0:
                        for _ in range(5):
                            pass
            else:
                pass
        else:
            pass
    else:
        if x == 0:
            pass
        elif x == 1:
            pass
        elif x == 2:
            pass
        elif x == 3:
            pass
        else:
            pass
    return x + y + z


def another_complex_func(a, b, c, d, e):
    result = 0
    for i in range(a):
        if i % 2 == 0:
            result += 1
        if i % 3 == 0:
            result += 2
        if i % 5 == 0:
            result += 3
        if i % 7 == 0:
            result += 4
        for j in range(b):
            if j > c:
                if d < e:
                    result += 10
                else:
                    result -= 5
            else:
                for k in range(10):
                    if k == 0 or k == 9:
                        result += 1
                    elif k == 5:
                        result += 2
    return result


def simple_func(x):
    return x * 2


def another_simple(a, b):
    if a > b:
        return a
    return b
