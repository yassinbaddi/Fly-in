venv:
	@uv venv

install:
	@uv pip install -r requirements.txt

add:
	@uv add $(pkg)

# in linux || true
run:
	@python main.py map.txt  || exit /b 0 

run_easy_1:
	@python main.py maps/easy/01_linear_path.txt 

run_easy_2:
	@python main.py maps/easy/02_simple_fork.txt 

run_easy_3:
	@python main.py maps/easy/01_linear_path.txt  

# -------------------------------------------------

run_medium_1:
	@python main.py maps/medium\01_dead_end_trap.txt 

run_medium_2:
	@python main.py maps/medium/02_circular_loop.txt

run_medium_3:
	@python main.py maps/medium/03_priority_puzzle.txt

# -------------------------------------------------

run_hard_1:
	@python main.py maps/hard\01_maze_nightmare.txt

run_hard_2:
	@python main.py maps/hard\02_capacity_hell.txt

run_hard_3:
	@python main.py maps/hard\03_ultimate_challenge.txt

# -------------------------------------------------

run-args:
	@uv run python main.py $(args)

sync:
	@uv pip compile requirements.txt -o uv.lock

.PHONY: clean



clean:
	@del /s /q *.pyc 2>nul
	@rmdir /s /q __pycache__ 2>nul