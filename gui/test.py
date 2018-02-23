PATH = "C:\\Users\\Developer\Desktop\\test_data\\test_analysis\\test1\individual_estimates\\"
base = 'parameters_00{}.sai.txt'


with open(PATH + base.format(1), 'r') as initial:
    lines = initial.read().splitlines()
    header = [line.split('=')[0].lstrip().rstrip() for line in lines]

print(";".join(header))
for i in [1, 2, 3, 5]:
    # Open file
    with open(PATH + base.format(i), 'r') as dataFile:
        # Read lines into a list
        lines = dataFile.read().splitlines()
        # Get dictionary with names and values
        header_and_values = {line.split('=')[0].rstrip().lstrip():
                             line.split('=')[-1].lstrip().rstrip() for line in lines}
        print(header_and_values)
        values = ';'.join([header_and_values[p] for p in header])
        print(values)


