# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

from machine import Machine


class A:
    pass
a = A()

def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    states = ['a', 'b', 'c']
    transitions = [
        ['a2b', 'a', 'b'],
        ['b2c', 'b', 'c'],
        ['c2a', 'c', 'a'],
    ]
    m = Machine(a, states=states, transitions=transitions, initial='a')
    print(a.state)
    a.a2b()
    print(a.state)
    a.to_c()
    print(a.state)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
