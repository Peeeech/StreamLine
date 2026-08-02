import os
import sys
import re

if __name__ == "__main__":
    files = os.listdir(sys.argv[1])
    for file in files:
        index = (re.split(r"_", file))[1]
        print(index)