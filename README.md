# scrum_tool
A simple ncurses based scrum tool

The general problem that this aims to solve is: how to manage the time of a team of people given a continuously growing and changing set of tasks with interdependencies.
The principle of of agile management is applied, along with a type of task scheduling that minimizes backtracking.
Individual workers are parametrized based on their performance on tasks, and this allows for optimal worker assignment and task allotment.

Typical install:
>>> git clone https://github.com/Joshuaalbert/scrum_tool.git
>>> cd scrum_tool && python setup.py install
>>> export PATH=${PWD}/bin/scrum_tool:${PATH}

Typical usage:
>>> mkdir some_path && cd !$
>>> scrum_tool

This will create a database file in some_path
