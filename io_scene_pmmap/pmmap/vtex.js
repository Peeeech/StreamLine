function newVertexColorManager() {
	var o = Object.assign({}, vertexColorManager);
	return o;
}

var vertexColorManager = {
	// vertex ID map to RGBA
	colorMap: undefined,
	// list of XYZ of vertex IDs
	triMap: undefined,
	// color groups: triplets, pairs, and singles
	groups: undefined,
	chunks: undefined,
	built: false,
	imgWidth: undefined,
	imgHeight: undefined,
	hasImage: false,
    // 2 = 50%, 4 = 25%, does not affect chunk size
    imgScale: 1,
	imgData: '',
	setMesh(key, tris, col) {
		if (!this.colorMap) this.colorMap = {};
		if (!this.triMap) this.triMap = {};
		if (!this.groups) this.groups = {};
		this.colorMap[key] = [];
		this.triMap[key] = [];
		this.groups[key] = [];
		for (var i in col) {
			var o = Object.assign({}, vColor);
			o.r = col[i][0];
			o.g = col[i][1];
			o.b = col[i][2];
			o.a = col[i][3];
			if (typeof o.a === 'undefined') o.a = 255;
			this.colorMap[key].push(o);
		}
		for (var i in tris) {
			this.triMap[key].push([tris[i][0], tris[i][1], tris[i][2]]);
			this.groups[key].push(this.newColorGroup(this.colorMap[key][tris[i][0]], this.colorMap[key][tris[i][1]], this.colorMap[key][tris[i][2]]));
		}
	},
	newColorGroup(c1, c2, c3) {
		var o = Object.assign({}, colorGroup);
		var d1v2 = c1.diff(c2);
		var d1v3 = c1.diff(c3);
		var d2v3 = c2.diff(c3);
		var dMin = Math.min(d1v2, d1v3, d2v3);
		var dMax = Math.max(d1v2, d1v3, d2v3);

		if (!dMax) {
			// just one
			o.c1 = c1;
		} else if (!dMin) {
			// just two
			o.d = 2;
			if (!d1v2) {
				// 1 and 2 are same
				o.c1 = c1;
				o.c2 = c3;
			} else {
				// 2 and 3 are same
				o.c1 = c1;
				o.c2 = c2;
			}
		} else {
			// all three
			o.d = 3;
			// we want 2->3 to be min and 1->2 to be max
			if (dMin == d1v2 && dMax == d1v3) {
				o.c1 = c3;
				o.c2 = c1;
				o.c3 = c2;
			} else if (dMin == d1v2 && dMax == d2v3) {
				o.c1 = c3;
				o.c2 = c2;
				o.c3 = c1;
			} else if (dMin == d1v3 && dMax == d1v2) {
				o.c1 = c2;
				o.c2 = c1;
				o.c3 = c3;
			} else if (dMin == d1v3 && dMax == d2v3) {
				o.c1 = c2;
				o.c2 = c3;
				o.c3 = c1;
			} else if (dMin == d2v3 && dMax == d1v2) {
				o.c1 = c1;
				o.c2 = c2;
				o.c3 = c3;
			} else if (dMin == d2v3 && dMax == d1v3) {
				o.c1 = c1;
				o.c2 = c3;
				o.c3 = c2;
			}
		}

		o.width = 4;
		o.height = 4;
		if (o.c2) {
			var dv = o.c1.diff(o.c2);
            if (this.imgScale > 1) dv /= this.imgScale;
			if (dv > 126) o.height = 256;
			else if (dv > 62) o.height = 128;
			else if (dv > 30) o.height = 64;
			else if (dv > 14) o.height = 32;
			else if (dv > 6) o.height = 16;
			else o.height = 64;
		}
		if (o.c3) {
			var dh = o.c2.diff(o.c3);
            if (this.imgScale > 1) dh /= this.imgScale;
			if (dh > 126) o.width = 256;
			else if (dh > 62) o.width = 128;
			else if (dh > 30) o.width = 64;
			else if (dh > 14) o.width = 32;
			else if (dh > 6) o.width = 16;
			else o.width = 8;
		}

		return o;
	},
	newChunk(sizeX, sizeY) {
		var o = Object.assign({}, imageChunk);
		o.width = sizeX;
		o.height = sizeY;
		return o;
	},
	build() {
		if (this.built) return;

		// gather all colors
		var orderedGroups = [];
		// current block size
		var level = 256;
		// 0: square, 1: skinny
		var ratio = 0;
		// number of colors
		var step = 3;
		this.gatherColors(orderedGroups, 256, 0, 3);
		this.gatherColors(orderedGroups, 256, 1, 3);
		this.gatherColors(orderedGroups, 256, 1, 2);
		this.gatherColors(orderedGroups, 128, 0, 3);
		this.gatherColors(orderedGroups, 128, 1, 3);
		this.gatherColors(orderedGroups, 128, 1, 2);
		this.gatherColors(orderedGroups, 64, 0, 3);
		this.gatherColors(orderedGroups, 64, 1, 3);
		this.gatherColors(orderedGroups, 64, 1, 2);
		this.gatherColors(orderedGroups, 32, 0, 3);
		this.gatherColors(orderedGroups, 32, 1, 3);
		this.gatherColors(orderedGroups, 32, 1, 2);
		this.gatherColors(orderedGroups, 16, 0, 3);
		this.gatherColors(orderedGroups, 16, 1, 3);
		this.gatherColors(orderedGroups, 16, 1, 2);
		this.gatherColors(orderedGroups, 4, 0, 1);

		// divide into chunks
		this.chunks = [];
		for (var i=0; i < orderedGroups.length; i++) {
			var supported = false;
			for (var j=0; j < this.chunks.length; j++) {
				if (this.chunks[j].checkFit(orderedGroups[i])) {
					this.chunks[j].add(orderedGroups[i]);
					supported = true;
					break;
				}
			}
			if (!supported) {
				var addChunk = this.newChunk(256,256);
				addChunk.add(orderedGroups[i]);
				this.chunks.push(addChunk);
			}
		}

		// figure out image size
		this.imgWidth = 256;
		this.imgHeight = 256;
		if (this.chunks.length == 1) {
			this.imgWidth = this.chunks[0].getWidth();
			this.imgHeight = this.chunks[0].getHeight();
		} else {
			while (this.imgWidth < 256*Math.sqrt(this.chunks.length)) {
				this.imgWidth *= 2;
			}
			this.imgHeight = 256 * Math.ceil(this.chunks.length / (this.imgWidth / 256));
		}

		// assign position to chunks
		var chunkX = 0;
		var chunkY = 0;
		for (var i=0; i < this.chunks.length; i++) {
			this.chunks[i].x = chunkX;
			this.chunks[i].y = chunkY;
			chunkX += 256;
			if (chunkX >= this.imgWidth) {
				chunkX = 0;
				chunkY += 256;
			}
		}

		// generate image data
		this.imgData = '';
		for (var pY=0; pY < this.imgHeight; pY++) {
			for (var pX=0; pX < this.imgWidth; pX++) {
				var pc = {r:255,g:255,b:255,a:255};
				for (var i=0; i < this.chunks.length; i++) {
					if (pX < this.chunks[i].x || pX >= this.chunks[i].x+this.chunks[i].width) continue;
					if (pY < this.chunks[i].y || pY >= this.chunks[i].y+this.chunks[i].height) continue;
					pc = this.chunks[i].drawPixel(pX-this.chunks[i].x, pY-this.chunks[i].y);
					if (!this.hasImage && (pc.r!=255 || pc.g!=255 || pc.b!=255 || pc.a!=255)) this.hasImage = true;
				}
				this.imgData += String.fromCharCode(pc.b);
				this.imgData += String.fromCharCode(pc.g);
				this.imgData += String.fromCharCode(pc.r);
				this.imgData += String.fromCharCode(pc.a);
			}
		}

		this.built = true;
	},
	gatherColors(myList, level, skinny, step) {
		for (var i in this.groups) {
			// each mesh
			for (var j=0; j < this.groups[i].length; j++) {
				var myGroup = this.groups[i][j];
				if (myGroup.d != step) continue;
				if (myGroup.height != level) continue;
				if (skinny && myGroup.width >= myGroup.height) continue;

				var supported = false;
				for (var k=0; k < myList.length; k++) {
					if (myList[k].checkSupport(myGroup)) {
						supported = true;
						break;
					}
				}
				if (!supported) {
					myList.push(myGroup);
				}
			}
		}
	},
	makeImage(width, height, data) {
		/*
		1 byte		ID length					Length of the image ID field
		1 byte		Color map type				Whether a color map is included
		1 byte		Image type					Compression and color types
		5 bytes		Color map specification		Describes the color map
		10 bytes	Image specification			Image dimensions and format
			X-origin (2 bytes): absolute coordinate of lower-left corner for displays where origin is at the lower left
			Y-origin (2 bytes): as for X-origin
			Image width (2 bytes): width in pixels
			Image height (2 bytes): height in pixels
			Pixel depth (1 byte): bits per pixel
			Image descriptor (1 byte): bits 3-0 give the alpha channel depth, bits 5-4 give direction
		*/
		var r = '';
		//ID is 0
		r += String.fromCharCode(0x00);
		//no color map
		r += String.fromCharCode(0x00);
		//image type is 2 = "uncompressed true-color image"
		r += String.fromCharCode(0x02);
		//no color map
		r += String.fromCharCode(0x00);
		r += String.fromCharCode(0x00);
		r += String.fromCharCode(0x00);
		r += String.fromCharCode(0x00);
		r += String.fromCharCode(0x00);
		//no origin nonsense
		r += String.fromCharCode(0x00);
		r += String.fromCharCode(0x00);
		r += String.fromCharCode(0x00);
		r += String.fromCharCode(0x00);
		//width (little endian)
		r += String.fromCharCode(width & 0xFF);
		r += String.fromCharCode(width >> 8);
		//height (little endian)
		r += String.fromCharCode(height & 0xFF);
		r += String.fromCharCode(height >> 8);
		//32bpp
		r += String.fromCharCode(0x20);
		//dunno what value means
		r += String.fromCharCode(0x20);

		//image data
		r += data;

		return r;
	},
	getImageLink(suffix) {
		this.build();
		if (this.hasImage) {
			var imagedata = this.makeImage(this.imgWidth, this.imgHeight, this.imgData);
			var name = 'vertexColors.tga';
			if (suffix && suffix !== '') {
				name = 'vertexColors'+suffix+'.tga';
			}
			var size = Math.round(imagedata.length/1024);
			return '<a download="'+name+'" href="data:image/tga;base64,'+btoa(imagedata)+'">'+name+' ('+size+' KB)</a>';
		}
	},
	getMeshUv(mesh, vert, tri) {
		//find matching chunk and calculate UV coordinate
		var uv = [0,0];
		var myColor = this.colorMap[mesh][vert];
		var myGroup = this.groups[mesh][tri];
		if (!myColor || !myGroup || !myGroup.hasColor(myColor)) return [0,0];
		for (var i=0; i < this.chunks.length; i++) {
			var myUV = this.chunks[i].getUvPixel(myGroup, myColor);
			if (myUV) {
				uv = myUV;
				break;
			}
		}
		//measure in pixels then convert
		return [uv[0]/(this.imgWidth), uv[1]/(this.imgHeight)];
	},
};

var vColor = {
	r: 0,
	g: 0,
	b: 0,
	a: 255,
	diff(other) {
		return Math.max(Math.abs(this.r - other.r), Math.abs(this.g - other.g), Math.abs(this.b - other.b), Math.abs(this.a - other.a));
	},
	match(other) {
		return (this.r == other.r && this.g == other.g && this.b == other.b && this.a == other.a);
	},
	key() {
		return ("00" + (+this.r).toString(16)).slice(-2).toUpperCase()+
			("00" + (+this.g).toString(16)).slice(-2).toUpperCase()+
			("00" + (+this.b).toString(16)).slice(-2).toUpperCase()+
			("00" + (+this.a).toString(16)).slice(-2).toUpperCase();
	},
};

var colorGroup = {
	c1: undefined,
	c2: undefined,
	c3: undefined,
	d: 1,
	height: 256,
	width: 256,
	hasColor(c) {
		if (this.c1 && this.c1.match(c)) return true;
		if (this.c2 && this.c2.match(c)) return true;
		if (this.c3 && this.c3.match(c)) return true;
	},
	match(other) {
		// number of colors must match
		if (this.d != other.d) return false;
		return this.checkSupport(other);
	},
	checkSupport(other) {
		if (this.d < other.d) return false;
		if (!this.hasColor(other.c1)) return false;
		if (other.d > 1 && !this.hasColor(other.c2)) return false;
		if (other.d > 2 && !this.hasColor(other.c3)) return false;
		return true;
	},
	drawPixel(x,y) {
		if (x < 0 || y < 0 || x > this.width || y > this.height) return false;
		if (this.d == 1) return {r:this.c1.r, g:this.c1.g, b:this.c1.b, a:this.c1.a};
		//one pixel buffer because texture blurring
		if (x > 0) x--;
		if (x == this.width - 1) x--;
		if (y > 0) y--;
		if (y == this.height - 1) y--;

		var gh = this.height-2;
		var yPer = y / gh;
		if (this.d == 2) {
			var inv = 1 - yPer;
			return {
				r:Math.round(this.c1.r*inv + this.c2.r*yPer),
				g:Math.round(this.c1.g*inv + this.c2.g*yPer),
				b:Math.round(this.c1.b*inv + this.c2.b*yPer),
				a:Math.round(this.c1.a*inv + this.c2.a*yPer),
			};
		}

		// entering the realm of VECTORS
		var gw = (this.width-2);
		var triLimit = gw * yPer;
		if (x > triLimit) x = parseInt(triLimit);
		var xPer = x / gw;

		//c1 = top left
		var u = parseFloat((1-yPer).toFixed(4));
		//c3 = bottom right
		var v = parseFloat(xPer.toFixed(4));
		//c2 = bottom left
		var w = (1-(u+v)).toFixed(4);
		if (w < 0) w = 0;

		var result = {
			r:Math.round(this.c1.r*u + this.c2.r*w + this.c3.r*v),
			g:Math.round(this.c1.g*u + this.c2.g*w + this.c3.g*v),
			b:Math.round(this.c1.b*u + this.c2.b*w + this.c3.b*v),
			a:Math.round(this.c1.a*u + this.c2.a*w + this.c3.a*v),
		};
		if (result.r > 255 || result.g > 255 || result.b > 255 || result.a > 255) throw 'rounding error';
		return result;
	},
	getUvPixel(c) {
		if (this.c1 && this.c1.match(c)) return [1, 1];
		if (this.c2 && this.c2.match(c)) return [1, this.height-1];
		if (this.c3 && this.c3.match(c)) return [this.width-1, this.height-1];
		return false;
	}
};

var imageChunk = {
	width: 256,
	height: 256,
	x: undefined,
	y: undefined,
	occ: undefined,
	check(x,y) {
		// gives the occupant at the given coordinates
		if (!this.occ) this.occ = [];
		for (var i = 0; i < this.occ.length; i++) {
			if (x >= this.occ[i].x && x < this.occ[i].x+this.occ[i].o.width && y >= this.occ[i].y && y < this.occ[i].y+this.occ[i].o.height) return this.occ[i];
		}
		return false;
	},
	findSpot(obj) {
		if (!obj.width || !obj.height || obj.width > this.width || obj.height > this.height) return false;
		var lookX = 0;
		var lookY = 0;
		while (lookY < this.height) {
			while (lookX < this.width) {
				maxX = lookX + obj.width - 1;
				maxY = lookY + obj.height - 1;
				if (!this.check(lookX, lookY) && !this.check(maxX, lookY) && !this.check(lookX, maxY) && !this.check(maxX, maxY)) {
					return [lookX, lookY];
				}
				lookX += obj.width;
			}
			lookY += obj.height;
			lookX = 0;
		}
	},
	checkFit(obj) {
		return !!this.findSpot(obj);
	},
	add(obj) {
		var found = this.findSpot(obj);
		if (!found) {
			console.error('Could not fit!', this, obj);
		}
		this.addOccupant(obj, found[0], found[1]);
	},
	addOccupant(obj,x,y) {
		// put it inside
		if (!this.occ) this.occ = [];
		this.occ.push({x: x, y: y, o: obj});
	},
	drawPixel(x,y) {
		var occ = this.check(x,y);
		if (occ) {
			return occ.o.drawPixel(x - occ.x, y - occ.y);
		}
		//default
		return {r:255,g:255,b:255,a:255};
	},
	getHeight() {
		if (!this.occ) this.occ = [];
		var max = 0;
		for (var i = 0; i < this.occ.length; i++) {
			var myMax = this.occ[i].y+this.occ[i].o.height;
			if (myMax > max) max = myMax;
			if (myMax >= this.height) break;
		}
		if (max > 128) return 256;
		if (max > 64) return 128;
		if (max > 32) return 64;
		if (max > 16) return 32;
		if (max > 8) return 16;
		return max;
	},
	getWidth() {
		if (!this.occ) this.occ = [];
		var max = 0;
		for (var i = 0; i < this.occ.length; i++) {
			var myMax = this.occ[i].x+this.occ[i].o.width;
			if (myMax > max) max = myMax;
			if (myMax >= this.width) break;
		}
		if (max > 128) return 256;
		if (max > 64) return 128;
		if (max > 32) return 64;
		if (max > 16) return 32;
		if (max > 8) return 16;
		return max;
	},
	findSupport(col) {
		if (!this.occ) this.occ = [];
		for (var i = 0; i < this.occ.length; i++) {
			if (this.occ[i].o.checkSupport(col)) {
				return this.occ[i];
			}
		}
		return false;
	},
	checkSupport(col) {
		return !!this.findSupport(col);
	},
	getUvPixel(group, col) {
		//for (var i = 0; i < this.occ.length; i++) {
		//if (this.occ[i].o.match(group)) {
		//}
		var findOcc = this.findSupport(group);
		if (findOcc) {
			var raw = findOcc.o.getUvPixel(col);
			return [raw[0]+findOcc.x+this.x, raw[1]+findOcc.y+this.y];
		}
		return false;
	},
};

module.exports = {
    newVertexColorManager
};