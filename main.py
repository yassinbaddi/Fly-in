import sys
from simulation.engine import COLORS, RESET
from visualization.gui import GUI


def main() -> None:
    """Run the application."""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <map_file>")
        sys.exit(1)
    try:
        GUI(sys.argv[1]).run()
    except Exception as err:
        print(COLORS[0],"Error: ", err, RESET)
        sys.exit(1)
    except KeyboardInterrupt:
        print(COLORS[2],"Keyboard Interrupt", RESET)
        sys.exit(130)


if __name__ == "__main__":
    main()