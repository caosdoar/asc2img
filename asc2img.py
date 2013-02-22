import Image
import argparse
import array
import math

VERSION = '0.1'

class ArcInfo(object):
	'ArcInfo ASCII Grid file'
	def __init__(self, ncols, nrows, xllcorner, yllcorner, cellsize, nodata_val, data):
		self.ncols = ncols
		self.nrows = nrows
		self.xllcorner = xllcorner
		self.yllcorner = yllcorner
		self.cellsize = cellsize
		self.nodata_val = nodata_val
		self.data = data
		self._max_val = None

	@staticmethod
	def load(filename):
		fd = open(filename)
		data = array.array('f')

		line = fd.readline()
		assert(line.lower().startswith('ncols'))
		ncols = int(line.strip().split()[1])

		line = fd.readline()
		assert(line.lower().startswith('nrows'))
		nrows = int(line.strip().split()[1])

		line = fd.readline()
		assert(line.lower().startswith('xllcorner'))
		xllcorner = float(line.strip().split()[1])

		line = fd.readline()
		assert(line.lower().startswith('yllcorner'))
		yllcorner = float(line.strip().split()[1])

		line = fd.readline()
		assert(line.lower().startswith('cellsize'))
		cellsize = float(line.strip().split()[1])

		line = fd.readline()
		nodata_val = -999
		if line.lower().startswith('nodata_value'):
			nodata_val = float(line.strip().split()[1])
		else:
			line_data = [float(x) for x in line.strip().split()]
			data.fromlist(line_data)

		for line in fd:
			line_data = [float(x) for x in line.strip().split()]
			data.fromlist(line_data)

		fd.close()
		return ArcInfo(ncols, nrows, xllcorner, yllcorner, cellsize, nodata_val, data)

	@property
	def max(self):
		if self._max_val is None:
			self._max_val = max(self.data)
		return self._max_val

	def get(self, x, y):
		return self.data[x + y * self.ncols]


class Raster(object):
	def __init__(self):
		self.layer_images = []

	def raster(self, arc_info, img):
		min_val, max_val = self.range(arc_info)
		if img.mode == 'L':
			self._raster_grayscale(arc_info, img, min_val, max_val)
		elif img.mode == 'RGB':
			self._raster_rgb(arc_info, img, min_val, max_val)
		elif img.mode == 'F':
			self._raster_float(arc_info, img, min_val, max_val)

	def _raster_grayscale(self, arc_info, img, min_val, max_val):
		pixdata = img.load()
		for y in xrange(img.size[1]):
		    for x in xrange(img.size[0]):
		        c = int(self.scale_value(min_val, max_val, arc_info.get(x, y), 0, 255))
		        pixdata[x, y] = c

	def _raster_rgb(self, arc_info, img, min_val, max_val):
		pixdata = img.load()
		n_layers = len(self.layer_images)
		for y in xrange(img.size[1]):
		    for x in xrange(img.size[0]):
		    	h = arc_info.get(x, y)
		    	rgb = (0, 0, 0)
		        if h < min_val:
		        	img0 = self.layer_images[0]
		        	rgb = img0.getpixel((x % img0.size[0], y % img0.size[1]))
		        elif h >= max_val:
		        	img0 = self.layer_images[-1]
		        	rgb = img0.getpixel((x % img0.size[0], y % img0.size[1]))
		        else:
		        	f = (n_layers - 1) * h / (max_val - min_val)
		        	i = int(math.floor(f))
		        	t = f - i
		        	t_inv = 1 - t
		        	img0 = self.layer_images[i]
		        	img1 = self.layer_images[i + 1]
		        	p0 = img0.getpixel((x % img0.size[0], y % img0.size[1]))
		        	p1 = img1.getpixel((x % img1.size[0], y % img1.size[1]))
		        	rgb = (int(p0[0] * t_inv + p1[0] * t),\
		        		int(p0[1] * t_inv + p1[1] * t), \
		        		int(p0[2] * t_inv + p1[2] * t))
		        pixdata[x, y] = rgb

	def _raster_float(self, arc_info, img, min_val, max_val):
		pixdata = img.load()
		for y in xrange(img.size[1]):
		    for x in xrange(img.size[0]):
		    	val = arc_info.get(x, y)
		    	clamped_val = min(max(val, min_val), max_val)
		        pixdata[x, y] = clamped_val

	def add_layer_image(self, img):
		self.layer_images.append(img)

	def range(self, arc_info):
		return 0, arc_info.max

	def scale_value(self, in_min, in_max, val, out_min, out_max):
		if val < in_min:
			return out_min
		return (val - in_min) / (in_max - in_min) * (out_max - out_min) + out_min


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(
        description='ArcInfo ASCII Grid file raster v%s' % (VERSION))
    arg_parser.add_argument('-f', '--format', 
        choices=['L', 'RGB', 'F'], 
        default='L', 
        help='Output image format.')
    arg_parser.add_argument('in_filename', nargs=1, help='Path to ".asc" a file.')
    arg_parser.add_argument('out_filename', nargs=1, help='Path to the output image file.')
    arg_parser.add_argument('color_layers', nargs='*', help='Path to the color image sorted by height.')
    args = arg_parser.parse_args()

    print('Reading input file...')
    asc = ArcInfo.load(args.in_filename[0])
    print('Creating empty image...')
    img = Image.new(args.format, (asc.ncols, asc.nrows))
    raster = Raster()
    for color_layer in args.color_layers:
    	layer_img = Image.open(color_layer)
    	raster.add_layer_image(layer_img)
    print('Rasterizing image...')
    raster.raster(asc, img)
    print('Saving image...')
    img.save(args.out_filename[0])
    print('Done.')


