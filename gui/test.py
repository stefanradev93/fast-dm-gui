

PATH = "C:\\Users\\Developer\\Desktop\\Projects\\" \
       "fast_dm_builds\\fast-dm1.0\\test_output\\test2\\individual_estimates\\"
base = 'parameters_'
name = '0.txt'
# Open file
with open(PATH + base + name, 'r') as dataFile:
    # Read lines into a list
    lines = dataFile.read().splitlines()
    # Get header and values
    header = ['dataset'] + [line.split('=')[0].rstrip() for line in lines]
    values = [name] + [line.split('=')[-1].lstrip() for line in lines]

    # Convert to strings
    headerLine = ';'.join(header)
    valuesLine = ';'.join(values)
    print(headerLine)
    print(valuesLine)