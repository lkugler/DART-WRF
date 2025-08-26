#!/usr/bin/python
"""Script to pretty-pring a config file (pickle format)"

Usage:
    python print_config.py <config_file>
"""
import sys, pickle, pprint

if __name__ == '__main__':
    f = sys.argv[1]
    with open(f, 'rb') as f:
        cfg = pickle.load(f)

    pprint.pprint(cfg)