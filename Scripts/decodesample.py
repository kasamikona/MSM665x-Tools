import sys, struct

CLK = 256000
SAMPLE_RATE_DIVIDERS = [32, 24, 20, 8, 64, 48, 40, 16]

METHOD_ADPCM = 0
METHOD_PCM = 1
METHOD_MELODY = 2

oki_step_table = [
	 16,  17,  19,  21,   23,   25,   28,   31,   34,  37,
	 41,  45,  50,  55,   60,   66,   73,   80,   88,  97,
	107, 118, 130, 143,  157,  173,  190,  209,  230, 253,
	279, 307, 337, 371,  408,  449,  494,  544,  598, 658,
	724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552
]

adpcm_index_table = [
	-1, -1, -1, -1, 2, 4, 6, 8,
	-1, -1, -1, -1, 2, 4, 6, 8,
]

class ADPCM_State:
	def __init__(self):
		self.step_index = 0
		self.predictor = 0

def decode_pcm8(data):
	# Turn u8 to s16
	data_decoded = [0]*len(data)
	for i in range(len(data)):
		data_decoded[i] = (data[i]-128)*256
	return data_decoded

def adpcm_decode_nybble(state, nybble):
	step = oki_step_table[state.step_index]
	state.step_index += adpcm_index_table[nybble]
	state.step_index = min(max(state.step_index, 0), 48)

	diff = step>>3
	if nybble & 4:
		diff += step
	if nybble & 2:
		diff += step>>1
	if nybble & 1:
		diff += step>>2

	if nybble & 8:
		state.predictor -= diff
	else:
		state.predictor += diff
	state.predictor = min(max(state.predictor, -2048), 2047)

	return state.predictor * 16

def decode_adpcm4(data):
	data_decoded = [0]*(len(data)*2)
	state_step_index = 0
	state = ADPCM_State()
	for i in range(len(data)):
		nybble1 = data[i]>>4
		nybble2 = data[i]&15
		data_decoded[2*i] = adpcm_decode_nybble(state, nybble1)
		data_decoded[2*i+1] = adpcm_decode_nybble(state, nybble2)

	return data_decoded;

def main():
	if len(sys.argv) < 2:
		print(sys.argv[0], "<rom> <phrase num>")
		return
	
	with open(sys.argv[1], "rb") as f:
		data = f.read()
	
	phrase_num = int(sys.argv[2])
	
	if phrase_num < 1 or phrase_num > 127:
		print("Phrase number out of range")
		return
	
	p = 0x800+(phrase_num*4)
	phrase_data = struct.unpack(">I", data[p:p+4])[0]
	phrase_addr = phrase_data & 0xFFFFFF
	phrase_flags = phrase_data >> 24
	
	if phrase_addr < 0xB00:
		print("Phrase is blank")
		return
	
	playback_method = phrase_flags >> 6
	sample_rate = CLK/SAMPLE_RATE_DIVIDERS[phrase_flags&7]
	
	if playback_method == 3:
		print("Invalid playback method")
		return
	
	sample_data = b""
	while True:
		chunk_size = data[phrase_addr]
		if chunk_size == 0:
			break
		sample_data += data[phrase_addr+1:phrase_addr+1+chunk_size]
		phrase_addr += 1+chunk_size
	print("Read {0:d} bytes of sample data".format(len(sample_data)))
	
	print("Sample rate: {0:.1f}".format(sample_rate))
	
	if playback_method == METHOD_ADPCM:
		print("Playback method: ADPCM")
		data_decoded = decode_adpcm4(sample_data)
	elif playback_method == METHOD_PCM:
		print("Playback method: PCM")
		data_decoded = decode_pcm8(sample_data)
	else:
		print("Playback method: Melody (NOT IMPLEMENTED)")
		return
	
	with open(sys.argv[1]+"_phrase{0:d}.bin".format(phrase_num), "wb") as f:
		# Write wav header TODO
		for s in data_decoded:
			f.write(struct.pack("<h", s))
		print("Wrote data to", f.name)

if __name__ == "__main__":
	main()