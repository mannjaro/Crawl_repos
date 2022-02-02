from dotenv import load_dotenv

from get_meta import get_meta
from choise import check

load_dotenv()


def main():
    get_meta()
    check()


if __name__ == '__main__':
    main()
