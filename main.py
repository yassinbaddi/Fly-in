import sys
from visualization.gui import GUI


def main() -> None:
    """Run the application."""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <map_file>")
        sys.exit(1)
    try:
        GUI(sys.argv[1]).run()
    except Exception as err:
        print("Error: ", err)
        sys.exit()


if __name__ == "__main__":
    main()