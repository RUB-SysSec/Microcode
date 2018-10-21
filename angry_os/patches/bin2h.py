# binary file to c header conversion utility
# credits: wiki.osdev.org, syssec.rub.de

import sys
import struct

if len(sys.argv) != 3:
	print('Usage: bin2h.py in.bin out.h')

else:
	with open(sys.argv[1], 'rb') as infile:
		with open(sys.argv[2], 'w') as outfile:

			outfile.write('#pragma once\n\n')
			outfile.write('#include <stdint.h>\n\n')
			outfile.write('uint8_t array_name[] = {\n')


			infile.seek(0, 2)
			size = infile.tell()
			infile.seek(0, 0)

			for i in range(size):
				byte = struct.unpack('<B', infile.read(1))[0]
				outfile.write('0x%02x' % byte)

				if i < size - 1:
					outfile.write(', ')

				if i % 16 == 15:
					outfile.write('\n')

			outfile.write('};')