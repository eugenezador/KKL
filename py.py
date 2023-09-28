list = []
file1 = open("angles.txt", 'r')
Lines = file1.readlines()
 
for line in Lines:
    list.append(float(line))

list1 = []
file2 = open("wave_numbers.txt", 'r')
Lines2 = file2.readlines()
 
for line in Lines2:
    list1.append(float(line))


file = open("test.txt", "w")
for index in range(10):
    st = str(list[index]) + " " + str(list1[index]) + "\n"
    file.write(st)
file.close()