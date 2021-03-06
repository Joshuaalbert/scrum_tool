# scrum_tool
A simple ncurses based scrum tool

The general problem that this aims to solve is: how to manage the time of a team of people given a continuously growing and changing set of tasks with interdependencies.
The principle of of agile management is applied, along with a type of task scheduling that minimizes backtracking.
Individual workers are parametrized based on their performance on tasks, and this allows for optimal worker assignment and task allotment.

Typical install:
``` bash
git clone https://github.com/Joshuaalbert/scrum_tool.git
cd scrum_tool && python setup.py install
```

Quick and dirty usage:
``` bash
cd src/scrum_tool
python scrum_tool.py
```

This will create a database file in some_path. Pressing '?' in any screen will tell you the available commands.

# Suggestions very welcome
Start an issue for bugs or requests!
