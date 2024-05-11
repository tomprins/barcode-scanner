import pandas as pd
import requests
import usb.core
import usb.util
import smbus2 as smbus
import time
import os

EURO_SYMBOL = bytearray([0x00, 0x06, 0x09, 0x1C, 0x08, 0x1C, 0x09, 0x06])
CURRENT_DIR = os.getcwd()
BARCODE_COLUMN_NAME = "Variant Barcode"
PRICE_COLUMN_NAME = "Variant Price"
TITLE_COLUMN_NAME = "Title"

I2C_ADDR  = 0x27
LCD_WIDTH = 16
LCD_CHR = 1
LCD_CMD = 0
LCD_CHARS = [0x40, 0x48, 0x50, 0x58, 0x60, 0x68, 0x70, 0x78]
LCD_LINE_1 = 0x80
LCD_LINE_2 = 0xC0
LCD_LINE_3 = 0x94
LCD_LINE_4 = 0xD4
LCD_BACKLIGHT  = 0x08
ENABLE = 0b00000100
E_PULSE = 0.0005
E_DELAY = 0.00059789000342679

bus = smbus.SMBus(0)

def delete_existing_csv():
	folder = os.listdir(CURRENT_DIR)
	for item in folder:
		if item.endswith(".csv"): os.remove(os.path.join(CURRENT_DIR, item))

def get_new_csv():
	response = requests.get("https://app.matrixify.app/files/speldorado/a3fc286d6beedcb02b1611681bd3445c/prijslijst-scanners.csv")	
	delete_existing_csv()

	with open("prijslijst-scanner.csv", "wb") as file:
		file.write(response.content)
		return pd.read_csv("prijslijst-scanner.csv")

def get_barcode_scanner():
	dev = usb.core.find(idVendor=0x0525, idProduct=0xa4ac)
	if dev is None:
		raise ValueError('USB device not found')

	if dev.is_kernel_driver_active(0):
		dev.detach_kernel_driver(0)
		print("Detached USB device from kernel driver")

	dev.set_configuration()
	cfg = dev.get_active_configuration()
	intf = cfg[(0,0)]
	barcode_scanner = usb.util.find_descriptor(intf, custom_match = lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)

	return barcode_scanner

def lcd_init():
  lcd_byte(0x33,LCD_CMD)
  lcd_byte(0x32,LCD_CMD)
  lcd_byte(0x06,LCD_CMD)
  lcd_byte(0x0C,LCD_CMD)
  lcd_byte(0x28,LCD_CMD)
  lcd_byte(0x01,LCD_CMD)
  time.sleep(E_DELAY)

def lcd_byte(bits, mode):
  bits_high = mode | (bits & 0xF0) | LCD_BACKLIGHT
  bits_low = mode | ((bits<<4) & 0xF0) | LCD_BACKLIGHT

  bus.write_byte(I2C_ADDR, bits_high)
  lcd_toggle_enable(bits_high)

  bus.write_byte(I2C_ADDR, bits_low)
  lcd_toggle_enable(bits_low)

def lcd_toggle_enable(bits):
  time.sleep(E_DELAY)
  bus.write_byte(I2C_ADDR, (bits | ENABLE))
  time.sleep(E_PULSE)
  bus.write_byte(I2C_ADDR,(bits & ~ENABLE))
  time.sleep(E_DELAY)

def lcd_string(message,line):
  message = message.ljust(LCD_WIDTH," ")
  lcd_byte(line, LCD_CMD)

  for i in range(LCD_WIDTH): lcd_byte(ord(message[i]),LCD_CHR)
	
def lcd_custom(charPos, charDef):
	lcd_byte(LCD_CHARS[charPos], LCD_CMD)
	for line in charDef: lcd_byte(line, LCD_CHR)

conv_table = {
		0:['', ''],
		4:['a', 'A'],
		5:['b', 'B'],
		6:['c', 'C'],
		7:['d', 'D'],
		8:['e', 'E'],
		9:['f', 'F'],
		10:['g', 'G'],
		11:['h', 'H'],
		12:['i', 'I'],
		13:['j', 'J'],
		14:['k', 'K'],
		15:['l', 'L'],
		16:['m', 'M'],
		17:['n', 'N'],
		18:['o', 'O'],
		19:['p', 'P'],
		20:['q', 'Q'],
		21:['r', 'R'],
		22:['s', 'S'],
		23:['t', 'T'],
		24:['u', 'U'],
		25:['v', 'V'],
		26:['w', 'W'],
		27:['x', 'X'],
		28:['y', 'Y'],
		29:['z', 'Z'],
		30:['1', '!'],
		31:['2', '@'],
		32:['3', '#'],
		33:['4', '$'],
		34:['5', '%'],
		35:['6', '^'],
		36:['7' ,'&'],
		37:['8', '*'],
		38:['9', '('],
		39:['0', ')'],
		40:['\n', '\n'],
		41:['\x1b', '\x1b'],
		42:['\b', '\b'],
		43:['\t', '\t'],
		44:[' ', ' '],
		45:['_', '_'],
		46:['=', '+'],
		47:['[', '{'],
		48:[']', '}'],
		49:['\\', '|'],
		50:['#', '~'],
		51:[';', ':'],
		52:["'", '"'],
		53:['`', '~'],
		54:[',', '<'],
		55:['.', '>'],
		56:['/', '?'],
		100:['\\', '|'],
		103:['=', '='],
		}

def binary_to_ASCII(byteList):
	shift=False
	if byteList[0] == 2:
		shift=True
	while True:
		have0s=False
		have2s=False
		if 0 in byteList:
			byteList.remove(0)
			have0s=True
		if 2 in byteList:
			byteList.remove(2)
			have2s=True
		if have0s==False and have2s==False:
			if len(byteList) >= 1:
				if shift == True: return conv_table[byteList[0]][1]
				else: return conv_table[byteList[0]][0] 
			else: return ''
		
# Try to reach google.com, if it timesout -> return False
def internet_on():
	for _ in range(10):	
		try:
			requests.get("http://www.google.com", timeout=None)
			return True
		except Exception as exception:
			time.sleep(5)
	
	return False		

def startLCD():
	lcd_init()
	lcd_custom(0, EURO_SYMBOL)

def data_to_barcode(data):
	barcode = ""
	for index in range(int(len(data)/8)): barcode += binary_to_ASCII(data[index*8 : index*8+8])
	
	if '\n' in barcode:
		barcode = barcode.rstrip('\n')
	
	return barcode

# 1,99 -> 1,99; 1.99 -> 1,99; 199 -> 1,99
def format_price(price):
    price = price.replace(".", ",")

    if "," not in price:
        price = price[:-2] + "," + price[-2:]

    if price.endswith(","):
        price += "0"

    return price
	

def main():
	try:			
		data = list(barcode_scanner.read(1000))
		barcode = data_to_barcode(data)
	
		# Check if barcode is in the csv file
		if barcode in barcode_list: # if yes -> display title and price on screen
			barcode_index = barcode_list.index(barcode)
			price = format_price(str(price_list[barcode_index]))
			title = title_list[barcode_index]

			lcd_string(title, LCD_LINE_1)
			lcd_string(chr(0)+price, LCD_LINE_2)
		else:
			lcd_string("Product niet", LCD_LINE_1)
			lcd_string("gevonden", LCD_LINE_2)

		time.sleep(5)
		lcd_byte(0x01, LCD_CMD)
		lcd_string("Scan uw product",LCD_LINE_1)
	
	except Exception as Argument:
		return


barcode_scanner = get_barcode_scanner()

if internet_on():
	df = get_new_csv()
else:	
	df = pd.read_csv(os.path.join(CURRENT_DIR, "prijslijst-scanner.csv"))

barcode_list = df[BARCODE_COLUMN_NAME].values.tolist()
price_list = df[PRICE_COLUMN_NAME].values.tolist()
title_list = df[TITLE_COLUMN_NAME].values.tolist()

startLCD()
lcd_string("Scan uw product", LCD_LINE_1)

while True:
	main()
