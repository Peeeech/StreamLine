
const gxDL = require('./gx_displaylist');
const vtex = require('./vtex');

//meshes
var result = {};
var useColor = true;
var useBake = false; //Untested after changing script for Node running, and I don't have any immediate interest in implementing.
var bakeSplit = false; //If you go on a whim and implement yourself, I'd appreciate you letting me (Peech) know so I can possibly implement for future release
var colorMan;
var skips = [];

//================= pulled from gxDL (undefined if pulled through req) =======
const VertexAttributeInput = {
    // TEXnMTXIDX are packed specially because of GL limitations.
    TEX0123MTXIDX: 0,
    TEX4567MTXIDX: 1,
    POS: 2,
    NRM: 3,
    // These are part of NBT in original GX. We pack them as separate inputs.
    BINRM: 4,
    TANGENT: 5,
    CLR0: 6,
    CLR1: 7,
    TEX01: 8,
    TEX23: 9,
    TEX45: 10,
    TEX67: 11,
    COUNT: 12
};

const GfxFormatU8_RGBA = gxDL.makeFormat(0x01, 0x04, 0b00000000);// = 66560
const GfxFormatU8_RGBA_NORM = gxDL.makeFormat(0x01, 0x04, 0b00000001);// = 66561
const GfxFormatU16_R = gxDL.makeFormat(0x02, 0x01, 0b00000000);// = 131328
const GfxFormatF32_R = gxDL.makeFormat(0x08, 0x01, 0b00000000);// = ?
const GfxFormatF32_RG = gxDL.makeFormat(0x08, 0x02, 0b00000000);// = 524800
const GfxFormatF32_RGB = gxDL.makeFormat(0x08, 0x03, 0b00000000);// = 525056
const GfxFormatF32_RGBA = gxDL.makeFormat(0x08, 0x04, 0b00000000);// = 525312

const vtxAttributeGenDefs = [
    { attrInput: VertexAttributeInput.POS,           name: "Position",      format: GfxFormatF32_RGBA },
    { attrInput: VertexAttributeInput.TEX0123MTXIDX, name: "TexMtx0123Idx", format: GfxFormatF32_RGBA },
    { attrInput: VertexAttributeInput.TEX4567MTXIDX, name: "TexMtx4567Idx", format: GfxFormatF32_RGBA },
    { attrInput: VertexAttributeInput.NRM,           name: "Normal",        format: GfxFormatF32_RGB },
    { attrInput: VertexAttributeInput.BINRM,         name: "Binormal",      format: GfxFormatF32_RGB },
    { attrInput: VertexAttributeInput.TANGENT,       name: "Tangent",       format: GfxFormatF32_RGB },
    { attrInput: VertexAttributeInput.CLR0,          name: "Color0",        format: GfxFormatF32_RGBA },
    { attrInput: VertexAttributeInput.CLR1,          name: "Color1",        format: GfxFormatF32_RGBA },
    { attrInput: VertexAttributeInput.TEX01,         name: "Tex01",         format: GfxFormatF32_RGBA },
    { attrInput: VertexAttributeInput.TEX23,         name: "Tex23",         format: GfxFormatF32_RGBA },
    { attrInput: VertexAttributeInput.TEX45,         name: "Tex45",         format: GfxFormatF32_RGBA },
    { attrInput: VertexAttributeInput.TEX67,         name: "Tex67",         format: GfxFormatF32_RGBA }
];


//====================== GLMatrix =======================================

function mat4mul(out, a, b) {
	let a00 = a[0],
	a01 = a[1],
	a02 = a[2],
	a03 = a[3];
	let a10 = a[4],
	a11 = a[5],
	a12 = a[6],
	a13 = a[7];
	let a20 = a[8],
	a21 = a[9],
	a22 = a[10],
	a23 = a[11];
	let a30 = a[12],
	a31 = a[13],
	a32 = a[14],
	a33 = a[15];
	// Cache only the current line of the second matrix
	let b0 = b[0],
	b1 = b[1],
	b2 = b[2],
	b3 = b[3];
	out[0] = b0 * a00 + b1 * a10 + b2 * a20 + b3 * a30;
	out[1] = b0 * a01 + b1 * a11 + b2 * a21 + b3 * a31;
	out[2] = b0 * a02 + b1 * a12 + b2 * a22 + b3 * a32;
	out[3] = b0 * a03 + b1 * a13 + b2 * a23 + b3 * a33;
	b0 = b[4];
	b1 = b[5];
	b2 = b[6];
	b3 = b[7];
	out[4] = b0 * a00 + b1 * a10 + b2 * a20 + b3 * a30;
	out[5] = b0 * a01 + b1 * a11 + b2 * a21 + b3 * a31;
	out[6] = b0 * a02 + b1 * a12 + b2 * a22 + b3 * a32;
	out[7] = b0 * a03 + b1 * a13 + b2 * a23 + b3 * a33;
	b0 = b[8];
	b1 = b[9];
	b2 = b[10];
	b3 = b[11];
	out[8] = b0 * a00 + b1 * a10 + b2 * a20 + b3 * a30;
	out[9] = b0 * a01 + b1 * a11 + b2 * a21 + b3 * a31;
	out[10] = b0 * a02 + b1 * a12 + b2 * a22 + b3 * a32;
	out[11] = b0 * a03 + b1 * a13 + b2 * a23 + b3 * a33;
	b0 = b[12];
	b1 = b[13];
	b2 = b[14];
	b3 = b[15];
	out[12] = b0 * a00 + b1 * a10 + b2 * a20 + b3 * a30;
	out[13] = b0 * a01 + b1 * a11 + b2 * a21 + b3 * a31;
	out[14] = b0 * a02 + b1 * a12 + b2 * a22 + b3 * a32;
	out[15] = b0 * a03 + b1 * a13 + b2 * a23 + b3 * a33;
	return out;
}

//====================== util =======================================
function assert(b, message) {
    if (!b) {
        console.error(new Error().stack);
        throw 'Assert fail: '+message;
    }
}

function assertExists(v, name = '') {
    if (v !== undefined && v !== null)
        return v;
    else
        throw 'Missing object '+name;
}

function readString(buffer, offs, length = -1, nulTerminated = true, encoding = null) {
    //buffer: ArrayBufferSlice
    //offs: number

    const buf = buffer.createTypedArray(Uint8Array, offs);
    let byteLength = 0;
    while (true) {
        if (length >= 0 && byteLength >= length)
            break;
        if (nulTerminated && buf[byteLength] === 0)
            break;
        byteLength++;
    }

    if (byteLength === 0)
        return "";

    if (encoding !== null) {
        return decodeString(buffer, offs, byteLength, encoding);
    } else {
        return copyBufferToString(buffer, offs, byteLength);
    }
}

function copyBufferToString(buffer, offs, byteLength) {
    //buffer: ArrayBufferSlice
    //offs: number
    //byteLength: number
    const buf = buffer.createTypedArray(Uint8Array, offs);
    let S = '';
    for (let i = 0; i < byteLength; i++)
        S += String.fromCharCode(buf[i]);
    return S;
}

function decodeString(buffer, offs, byteLength, encoding = 'utf8') {
    //buffer: ArrayBufferSlice
    //offs: number | undefined = undefined
    //byteLength: number | undefined = undefined
    //encoding = 'utf8'

    if (typeof TextDecoder !== 'undefined') {
        return new TextDecoder(encoding).decode(buffer.copyToBuffer(offs, byteLength));
    } else {
        throw "whoops";
    }
}

//====================== MathHelpers ================================
//(dst: mat4, scaleX: number, scaleY: number, scaleZ: number, rotationX: number, rotationY: number, rotationZ: number, translationX: number, translationY: number, translationZ: number): void
function computeModelMatrixSRT(dst, scaleX, scaleY, scaleZ, rotationX, rotationY, rotationZ, translationX, translationY, translationZ) {
    const sinX = Math.sin(rotationX), cosX = Math.cos(rotationX);
    const sinY = Math.sin(rotationY), cosY = Math.cos(rotationY);
    const sinZ = Math.sin(rotationZ), cosZ = Math.cos(rotationZ);

    dst[0] =  scaleX * (cosY * cosZ);
    dst[1] =  scaleX * (sinZ * cosY);
    dst[2] =  scaleX * (-sinY);
    dst[3] =  0.0;

    dst[4] =  scaleY * (sinX * cosZ * sinY - cosX * sinZ);
    dst[5] =  scaleY * (sinX * sinZ * sinY + cosX * cosZ);
    dst[6] =  scaleY * (sinX * cosY);
    dst[7] =  0.0;

    dst[8] =  scaleZ * (cosX * cosZ * sinY + sinX * sinZ);
    dst[9] =  scaleZ * (cosX * sinZ * sinY - sinX * cosZ);
    dst[10] = scaleZ * (cosY * cosX);
    dst[11] = 0.0;

    dst[12] = translationX;
    dst[13] = translationY;
    dst[14] = translationZ;
    dst[15] = 1.0;
}

//====================== Color ================================
//r: number, g: number, b: number, a: number = 1.0): Color
function colorNewFromRGBA(r, g, b, a = 1.0) {
    return { r, g, b, a };
}

//(dst: Color, n: number): void
function colorFromRGBA8(dst, n) {
    dst.r = ((n >>> 24) & 0xFF) / 0xFF;
    dst.g = ((n >>> 16) & 0xFF) / 0xFF;
    dst.b = ((n >>>  8) & 0xFF) / 0xFF;
    dst.a = ((n >>>  0) & 0xFF) / 0xFF;
}

//colorNewFromRGBA8(n: number): Color
function colorNewFromRGBA8(n) {
    const dst = colorNewFromRGBA(0, 0, 0, 0);
    colorFromRGBA8(dst, n);
    return dst;
}

//====================== Endian =====================================
const Endianness = {0: 'LITTLE_ENDIAN', 1: 'BIG_ENDIAN'}

const test = new Uint16Array([0xFEFF]);
const testView = new DataView(test.buffer);
const systemEndianness = (testView.getUint8(0) == 0xFF) ? Endianness.LITTLE_ENDIAN : Endianness.BIG_ENDIAN;

function getSystemEndianness() {
    return systemEndianness;
}

//====================== TopologyHelpers ================================
//topology: GfxTopology, baseVertex: number, numVertices: number): Uint16Array
function makeTriangleIndexBuffer(topology, baseVertex, numVertices) {
	const newSize = getTriangleIndexCountForTopologyIndexCount(topology, numVertices);
    const newBuffer = new Uint16Array(newSize);
    convertToTrianglesRange(newBuffer, 0, topology, baseVertex, numVertices);
    return newBuffer;
}

//dstBuffer: Uint16Array | Uint32Array | number[], dstOffs: number, topology: GfxTopology, baseVertex: number, numVertices: number
function convertToTrianglesRange(dstBuffer, dstOffs, topology, baseVertex, numVertices) {
	assert(dstOffs + getTriangleIndexCountForTopologyIndexCount(topology, numVertices) <= dstBuffer.length);

    let dst = dstOffs;
    if (topology === 3) {//GfxTopology.Quads
        for (let i = 0; i < numVertices; i += 4) {
            dstBuffer[dst++] = baseVertex + i + 0;
            dstBuffer[dst++] = baseVertex + i + 1;
            dstBuffer[dst++] = baseVertex + i + 2;
            dstBuffer[dst++] = baseVertex + i + 2;
            dstBuffer[dst++] = baseVertex + i + 3;
            dstBuffer[dst++] = baseVertex + i + 0;
        }
    } else if (topology === 1) {//GfxTopology.TriStrips
        for (let i = 0; i < numVertices - 2; i++) {
            if (i % 2 === 0) {
                dstBuffer[dst++] = baseVertex + i + 0;
                dstBuffer[dst++] = baseVertex + i + 1;
                dstBuffer[dst++] = baseVertex + i + 2;
            } else {
                dstBuffer[dst++] = baseVertex + i + 1;
                dstBuffer[dst++] = baseVertex + i + 0;
                dstBuffer[dst++] = baseVertex + i + 2;
            }
        }
    } else if (topology === 2) {//GfxTopology.TriFans
        for (let i = 0; i < numVertices - 2; i++) {
            dstBuffer[dst++] = baseVertex + 0;
            dstBuffer[dst++] = baseVertex + i + 1;
            dstBuffer[dst++] = baseVertex + i + 2;
        }
    } else if (topology === 4) {//GfxTopology.QuadStrips
        for (let i = 0; i < numVertices - 2; i += 2) {
            dstBuffer[dst++] = baseVertex + i + 0;
            dstBuffer[dst++] = baseVertex + i + 1;
            dstBuffer[dst++] = baseVertex + i + 2;
            dstBuffer[dst++] = baseVertex + i + 2;
            dstBuffer[dst++] = baseVertex + i + 1;
            dstBuffer[dst++] = baseVertex + i + 3;
        }
    } else if (topology === 0) {//GfxTopology.Triangles
        for (let i = 0; i < numVertices; i++)
            dstBuffer[dst++] = baseVertex + i;
    }
}

//topology: GfxTopology, indexBuffer: Uint16Array): Uint16Array
function convertToTriangleIndexBuffer(topology, indexBuffer) {
    if (topology === 0)//GfxTopology.TRIANGLES
        return indexBuffer;

    const newSize = getTriangleIndexCountForTopologyIndexCount(topology, indexBuffer.length);
    const newBuffer = new Uint16Array(newSize);
    convertToTriangles(newBuffer, 0, topology, indexBuffer);
    return newBuffer;
}

//topology: GfxTopology, indexCount: number): number
function getTriangleIndexCountForTopologyIndexCount(topology, indexCount) {
    // Three indexes per triangle.
    return 3 * getTriangleCountForTopologyIndexCount(topology, indexCount);
}

//topology: GfxTopology, indexCount: number): number
function getTriangleCountForTopologyIndexCount(topology, indexCount) {
    switch (topology) {
		case 0://GfxTopology.TRIANGLES
			// One triangle per every three indexes.
			return indexCount / 3;
		case 1://GfxTopology.TRISTRIP
		case 2://GfxTopology.TRIFAN
			// One triangle per index, minus the first two.
			return (indexCount - 2);
		case 3://GfxTopology.QUADS
			// Two triangles per four indices.
			return 2 * (indexCount / 4);
		case 4://GfxTopology.QUADSTRIP
			// Two triangles per two indexes, minus the first two.
			return 2 * (indexCount - 2);
    }
}

//dstBuffer: Uint16Array | Uint32Array, dstOffs: number, topology: GfxTopology, indexBuffer: Uint16Array | Uint32Array): void
function convertToTriangles(dstBuffer, dstOffs, topology, indexBuffer) {
    assert(dstOffs + getTriangleIndexCountForTopologyIndexCount(topology, indexBuffer.length) <= dstBuffer.length);

    let dst = dstOffs;
    if (topology === 3) {//GfxTopology.QUADS
        for (let i = 0; i < indexBuffer.length; i += 4) {
            dstBuffer[dst++] = indexBuffer[i + 0];
            dstBuffer[dst++] = indexBuffer[i + 1];
            dstBuffer[dst++] = indexBuffer[i + 2];
            dstBuffer[dst++] = indexBuffer[i + 0];
            dstBuffer[dst++] = indexBuffer[i + 2];
            dstBuffer[dst++] = indexBuffer[i + 3];
        }
    } else if (topology === 1) {//GfxTopology.TRISTRIP
        for (let i = 0; i < indexBuffer.length - 2; i++) {
            if (i % 2 === 0) {
                dstBuffer[dst++] = indexBuffer[i + 0];
                dstBuffer[dst++] = indexBuffer[i + 1];
                dstBuffer[dst++] = indexBuffer[i + 2];
            } else {
                dstBuffer[dst++] = indexBuffer[i + 1];
                dstBuffer[dst++] = indexBuffer[i + 0];
                dstBuffer[dst++] = indexBuffer[i + 2];
            }
        }
    } else if (topology === 2) {//GfxTopology.TRIFAN
        for (let i = 0; i < indexBuffer.length - 2; i++) {
            dstBuffer[dst++] = indexBuffer[0];
            dstBuffer[dst++] = indexBuffer[i + 1];
            dstBuffer[dst++] = indexBuffer[i + 2];
        }
    } else if (topology === 4) {//GfxTopology.QUADSTRIP
        for (let i = 0; i < indexBuffer.length - 2; i += 2) {
            dstBuffer[dst++] = indexBuffer[i + 0];
            dstBuffer[dst++] = indexBuffer[i + 1];
            dstBuffer[dst++] = indexBuffer[i + 2];
            dstBuffer[dst++] = indexBuffer[i + 2];
            dstBuffer[dst++] = indexBuffer[i + 1];
            dstBuffer[dst++] = indexBuffer[i + 3];
        }
    } else if (topology === 0) {//GfxTopology.TRIANGLES
        dstBuffer.set(indexBuffer, dstOffs);
    }
}

//====================== PM World =======================================
const MaterialLayer = {
    OPAQUE: 0x00,
    ALPHA_TEST: 0x01,
    BLEND: 0x02,
    OPAQUE_PUNCHTHROUGH: 0x03,
    ALPHA_TEST_PUNCHTHROUGH: 0x04,
}

const DrawModeFlags = {
    IS_DECAL: 0x10,
}

const CollisionFlags = {
    WALK_SLOW: 0x00000100,
    HAZARD_RESPAWN_ENABLED: 0x40000000,
}

//mat4.create
const trans = [
	1, 0, 0, 0,
	0, 1, 0, 0,
	0, 0, 1, 0,
	0, 0, 0, 1
];
const rot = [
	1, 0, 0, 0,
	0, 1, 0, 0,
	0, 0, 1, 0,
	0, 0, 0, 1
];
const scale = [
	1, 0, 0, 0,
	0, 1, 0, 0,
	0, 0, 1, 0,
	0, 0, 0, 1
];

//function calcTexMtx(dst: mat4, translationS: number, translationT: number, scaleS: number, scaleT: number, rotation: number, centerS: number, centerT: number): void {
function calcTexMtx(dst, translationS, translationT, scaleS, scaleT, rotation, centerS, centerT) {
    const theta = (Math.PI / 180) * -rotation;//MathConstants.DEG_TO_RAD
    const sinR = Math.sin(theta);
    const cosR = Math.cos(theta);

    dst[12] = scaleS * (0.5 * centerS);
    dst[13] = scaleT * (0.5 * centerT - 1.0);

    rot[0]  =  cosR;
    rot[4]  = -sinR;

    rot[1]  =  sinR;
    rot[5]  =  cosR;

    trans[12] = scaleS * -(0.5 * centerS);
    trans[13] = scaleT * -(0.5 * centerT - 1.0);

    scale[0] = scaleS;
    scale[5] = scaleT;

    mat4mul(rot, rot, dst);
    mat4mul(rot, trans, rot);
    mat4mul(dst, scale, rot);

    dst[12] += translationS;
    dst[13] += -translationT;
}

//export function mapSetMaterialTev(mb: GXMaterialBuilder, texCount: number, tevMode: number): void {
function mapSetMaterialTev(mb, texCount, tevMode) {
    //...
}

//export function parse(buffer: ArrayBufferSlice): TTYDWorld {
function parse(buffer) {
    const view = buffer.createDataView();

    const fileSize = view.getUint32(0x00);
    const mainDataSize = view.getUint32(0x04);
    const pointerFixupTableCount = view.getUint32(0x08);
    const namedChunkTableCount = view.getUint32(0x0C);

    const mainDataOffs = 0x20;
    const pointerFixupTableOffs = mainDataOffs + mainDataSize;
    const namedChunkTableOffs = pointerFixupTableOffs + (pointerFixupTableCount * 0x04);

    const chunkNames = [
        'animation_table',
        'curve_table',
        'fog_table',
        'information',
        'light_table',
        'material_name_table',
        'texture_table',
        'vcd_table',
    ];

    const isVersion102 = namedChunkTableCount === 8;
    const isVersion100 = namedChunkTableCount === 7;
    assert(isVersion100 || isVersion102);

    const chunkOffsets = []; //number[]

    // Read the chunks.
    let namedChunkTableIdx = namedChunkTableOffs;
    const namedChunkStringTableOffs = namedChunkTableOffs + (namedChunkTableCount * 0x08);
    for (let i = 0; i < namedChunkTableCount; i++) {
        const chunkOffs = mainDataOffs + view.getUint32(namedChunkTableIdx + 0x00);
        const chunkNameOffs = namedChunkStringTableOffs + view.getUint32(namedChunkTableIdx + 0x04);
        const chunkName = readString(buffer, chunkNameOffs, 0xFF, true);
        assert(chunkName === chunkNames[i]);
        chunkOffsets[i] = chunkOffs;
        namedChunkTableIdx += 0x08;
    }

	const animation_tableOffs = chunkOffsets[0];
	const curve_tableOffs = chunkOffsets[1];
	const fog_tableOffs = chunkOffsets[2];
	const informationOffs = chunkOffsets[3];
	const light_tableOffs = chunkOffsets[4];
	const material_name_tableOffs = chunkOffsets[5];
	const texture_tableOffs = chunkOffsets[6];
	const vcd_tableOffs = chunkOffsets[7];

    //#region texture_table
    const textureTableCount = view.getUint32(texture_tableOffs + 0x00);
    let textureTableIdx = texture_tableOffs + 0x04;
    const textureNameTable = [];//string[]
    for (let i = 0; i < textureTableCount; i++) {
        const textureNameOffs = mainDataOffs + view.getUint32(textureTableIdx + 0x00);
        let textureName = readString(buffer, textureNameOffs, 0x40, true);
        textureName = textureName.replace(/&/g, '_'); //replace unk with _
        textureNameTable[i] = textureName;
        textureTableIdx += 0x04;
    }
    //#endregion

    //#region fog_table
    const fogEnabled = !!view.getUint32(fog_tableOffs + 0x00);
    const fogMode = view.getUint32(fog_tableOffs + 0x04);
    const fogStartZ = view.getFloat32(fog_tableOffs + 0x08);
    const fogEndZ = view.getFloat32(fog_tableOffs + 0x0C);
    const fogColor = colorNewFromRGBA8(view.getUint32(fog_tableOffs + 0x10));
	const fogData = {
        enabled: fogEnabled,
        mode: fogMode,
        startZ: fogStartZ,
        endZ: fogEndZ,
        color: fogColor,
    };//FogData
    //#endregion

    //#region animation_table
const animationTableCount = view.getUint32(animation_tableOffs + 0x00);
let animationTableIdx = animation_tableOffs + 0x04;
const animations = [];
for (let i = 0; i < animationTableCount; i++) {
    const animationEntryOffs = mainDataOffs + view.getUint32(animationTableIdx + 0x00);
    animationTableIdx += 0x04;
    const nameOffs = mainDataOffs + view.getUint32(animationEntryOffs + 0x00);
    const name = readString(buffer, nameOffs, 0x40, true);
    const duration = view.getFloat32(animationEntryOffs + 0x08);
    const meshTrackTableRelOffs = view.getUint32(animationEntryOffs + 0x0C);
    const materialTrackTableRelOffs = view.getUint32(animationEntryOffs + 0x10);

    let meshAnimation = null;
    let materialAnimation = null;

    if (meshTrackTableRelOffs !== 0) {
        const meshTrackTableOffs = mainDataOffs + meshTrackTableRelOffs;
        const meshTrackTableCount = view.getUint32(meshTrackTableOffs + 0x00);
        let meshTrackTableIdx = meshTrackTableOffs + 0x04;
        const tracks = [];
        for (let j = 0; j < meshTrackTableCount; j++) {
            let trackEntryIdx = mainDataOffs + view.getUint32(meshTrackTableIdx + 0x00);
            const meshNameOffs = mainDataOffs + view.getUint32(trackEntryIdx + 0x00);
            const meshName = readString(buffer, meshNameOffs, 0x40, true);
            const translationOffsetX = view.getFloat32(trackEntryIdx + 0x04);
            const translationOffsetY = view.getFloat32(trackEntryIdx + 0x08);
            const translationOffsetZ = view.getFloat32(trackEntryIdx + 0x0C);
            const rotationOffsetX = view.getFloat32(trackEntryIdx + 0x10);
            const rotationOffsetY = view.getFloat32(trackEntryIdx + 0x14);
            const rotationOffsetZ = view.getFloat32(trackEntryIdx + 0x18);
            const scaleDividerX = view.getFloat32(trackEntryIdx + 0x1C);
            const scaleDividerY = view.getFloat32(trackEntryIdx + 0x20);
            const scaleDividerZ = view.getFloat32(trackEntryIdx + 0x24);
            const frameCount = view.getUint32(trackEntryIdx + 0x58);
            trackEntryIdx += 0x5C;

            const frames = [];
            for (let k = 0; k < frameCount; k++) {
                const time = view.getFloat32(trackEntryIdx + 0x00);
                trackEntryIdx += 0x04;

                const readComponent = () => {
                    const value = view.getFloat32(trackEntryIdx + 0x00);
                    const tangentIn = view.getFloat32(trackEntryIdx + 0x04);
                    const tangentOut = view.getFloat32(trackEntryIdx + 0x08);
                    const step = !!view.getUint32(trackEntryIdx + 0x10);
                    trackEntryIdx += 0x14;
                    meshTanIn = tangentIn;
                    meshTanOut = tangentOut;
                    return { value, tangentIn, tangentOut, step };
                };

                const translationX = readComponent();
                const translationY = readComponent();
                const translationZ = readComponent();
                const rotationX = readComponent();
                const rotationY = readComponent();
                const rotationZ = readComponent();
                const scaleX = readComponent();
                const scaleY = readComponent();
                const scaleZ = readComponent();

                // unk tracks
                trackEntryIdx += 0x14 * 12;

                frames.push({
                    time,
                    translationX, translationY, translationZ,
                    rotationX, rotationY, rotationZ,
                    scaleX, scaleY, scaleZ,
                });
            }

            meshTrackTableIdx += 0x04;
            tracks.push({
                meshName,
                translationOffsetX, translationOffsetY, translationOffsetZ,
                rotationOffsetX, rotationOffsetY, rotationOffsetZ,
                scaleDividerX, scaleDividerY, scaleDividerZ,
                frames,
            });
        }

        meshAnimation = { tracks };
    }

    if (materialTrackTableRelOffs !== 0) {
        const materialTrackTableOffs = mainDataOffs + materialTrackTableRelOffs;
        const materialTrackTableCount = view.getUint32(materialTrackTableOffs + 0x00);
        let materialTrackTableIdx = materialTrackTableOffs + 0x04;
        const tracks = [];
        for (let j = 0; j < materialTrackTableCount; j++) {
            let trackEntryIdx = mainDataOffs + view.getUint32(materialTrackTableIdx + 0x00);
            const materialNameOffs = mainDataOffs + view.getUint32(trackEntryIdx + 0x00);
            const materialName = readString(buffer, materialNameOffs, 0x40, true);
            const texGenIndex = view.getUint32(trackEntryIdx + 0x04);
            const centerS = view.getFloat32(trackEntryIdx + 0x08);
            const centerT = view.getFloat32(trackEntryIdx + 0x0C);
            const frameCount = view.getUint32(trackEntryIdx + 0x10);
            trackEntryIdx += 0x14;

            const frames = [];
            for (let k = 0; k < frameCount; k++) {
                const time = view.getFloat32(trackEntryIdx + 0x00);
                trackEntryIdx += 0x04;

                const readComponent = () => {
                    const value = view.getFloat32(trackEntryIdx + 0x00);
                    const tangentIn = view.getFloat32(trackEntryIdx + 0x04);
                    const tangentOut = view.getFloat32(trackEntryIdx + 0x08);
                    const step = !!view.getUint32(trackEntryIdx + 0x10);
                    trackEntryIdx += 0x14;
                    materialTanIn = tangentIn;
                    materialTanOut = tangentOut;
                    return { value, tangentIn, tangentOut, step };
                };

                const translationS = readComponent();
                const translationT = readComponent();
                const scaleS = readComponent();
                const scaleT = readComponent();
                const rotation = readComponent();
                frames.push({ time, translationS, translationT, scaleS, scaleT, rotation });
            }

            materialTrackTableIdx += 0x04;
            tracks.push({ materialName, texGenIndex, centerS, centerT, frames });
        }

        materialAnimation = { tracks };
    }
    animations.push({ name, duration, materialAnimation, meshAnimation });
    animationTableIdx + 0x04;
}
//#endregion

    //#region material_name_table
    const materialTableCount = view.getUint32(material_name_tableOffs + 0x00);
    let materialTableIdx = material_name_tableOffs + 0x04;
    const materialMap = {}; //new Map<number, Material>();
    const materials = [];//Material[]
    for (let i = 0; i < materialTableCount; i++) {
        const materialName = readString(buffer, mainDataOffs + view.getUint32(materialTableIdx + 0x00));
        const materialOffs = mainDataOffs + view.getUint32(materialTableIdx + 0x04);
        materialTableIdx += 0x08;

        // Parse material.
        const materialName2 = readString(buffer, mainDataOffs + view.getUint32(materialOffs + 0x00));
        assert(materialName === materialName2);
        const matColorReg = colorNewFromRGBA8(view.getUint32(materialOffs + 0x04));
        const matColorSrc = view.getUint8(materialOffs + 0x08);//GX.ColorSrc

        let materialLayer = MaterialLayer.OPAQUE;

        const materialLayerFlags = view.getUint8(materialOffs + 0x0A);//MaterialLayer
        assert(materialLayerFlags <= MaterialLayer.BLEND);
        materialLayer = Math.max(materialLayer, materialLayerFlags);

        const samplerEntryTableCount = view.getUint8(materialOffs + 0x0B);

        //const mb = new GXMaterialBuilder(materialName);

        const samplers = []; //Sampler[]
        const texMtx = []; //mat4[]
        const texData = []; //mat4[]
        let samplerEntryTableIdx = materialOffs + 0x0C;
        let xformTableIdx = materialOffs + 0x2C;
        for (let i = 0; i < samplerEntryTableCount; i++) {
            const samplerOffs = mainDataOffs + view.getUint32(samplerEntryTableIdx);
            const textureEntryOffs = mainDataOffs + view.getUint32(samplerOffs + 0x00);

            const samplerUnk04 = view.getUint32(samplerOffs + 0x04);
            assert(samplerUnk04 === 0x00000000);

            const wrapS = view.getUint8(samplerOffs + 0x08);//GX.WrapMode
            const wrapT = view.getUint8(samplerOffs + 0x09);//GX.WrapMode

            const materialLayerFlags = view.getUint8(samplerOffs + 0x0A);//MaterialLayer
            assert(materialLayerFlags <= MaterialLayer.BLEND);
            materialLayer = Math.max(materialLayer, materialLayerFlags);

            const textureName = readString(buffer, mainDataOffs + view.getUint32(textureEntryOffs + 0x00));

            // Seems to be some byte. Flags?
            const textureEntryUnk04 = view.getUint8(textureEntryOffs + 0x04);
            const textureWidth = view.getUint16(textureEntryOffs + 0x08);
            const textureHeight = view.getUint16(textureEntryOffs + 0x0A);
            const textureEntryUnk0C = view.getUint8(textureEntryOffs + 0x0C);
            assert(textureEntryUnk0C === 0x00);

            // For some reason, the game sets up samplers backwards.
            const backwardsIndex = samplerEntryTableCount - i - 1;

            const texMatrices = [
                30,//GX.TexGenMatrix.TEXMTX0
                33,//GX.TexGenMatrix.TEXMTX1
                36,//GX.TexGenMatrix.TEXMTX2
                39,//GX.TexGenMatrix.TEXMTX3
                42,//GX.TexGenMatrix.TEXMTX4
                45,//GX.TexGenMatrix.TEXMTX5
                48,//GX.TexGenMatrix.TEXMTX6
                51,//GX.TexGenMatrix.TEXMTX7
            ];

            //mb.setTexCoordGen(GX.TexCoordID.TEXCOORD0 + i, GX.TexGenType.MTX2x4, GX.TexGenSrc.TEX0 + backwardsIndex, texMatrices[backwardsIndex]);
            samplers[backwardsIndex] = { textureName, wrapS, wrapT };

            const translationS = view.getFloat32(xformTableIdx + 0x00);
            const translationT = view.getFloat32(xformTableIdx + 0x04);
            const scaleS = view.getFloat32(xformTableIdx + 0x08);
            const scaleT = view.getFloat32(xformTableIdx + 0x0C);
            const rotation = view.getFloat32(xformTableIdx + 0x10);
            const centerS = view.getFloat32(xformTableIdx + 0x14);
            const centerT = view.getFloat32(xformTableIdx + 0x18);
			//mat4.create
            texMtx[backwardsIndex] = [
				1, 0, 0, 0,
				0, 1, 0, 0,
				0, 0, 1, 0,
				0, 0, 0, 1
			];
            calcTexMtx(texMtx[backwardsIndex], translationS, translationT, scaleS, scaleT, rotation, centerS, centerT);
			texData[backwardsIndex] = {translationS, translationT, scaleS, scaleT, rotation, centerS, centerT};

            samplerEntryTableIdx += 0x04;
            xformTableIdx += 0x1C;
        }

        //mb.setChanCtrl(GX.ColorChannelID.COLOR0A0, false, GX.ColorSrc.VTX, matColorSrc, 0, GX.DiffuseFunction.NONE, GX.AttenuationFunction.NONE);

        const tevConfigRelOffs = view.getUint32(materialOffs + 0x110);
        let tevMode = 0;
        if (tevConfigRelOffs !== 0) {
            const tevConfigOffs = mainDataOffs + tevConfigRelOffs;
            tevMode = view.getUint8(tevConfigOffs + 0x00);
        }

        //mapSetMaterialTev(mb, samplerEntryTableCount, tevMode);

        //if (materialLayer === MaterialLayer.OPAQUE) {........

        //const gxMaterial = mb.finish();
        const gxMaterial = null;

        const material = { index: i, name: materialName, materialLayer, samplers, gxMaterial, matColorReg, texMtx, texData }; //Material
        //materialMap.set(materialOffs, material);
		materialMap[materialOffs] = material;
        materials.push(material);
    }
    //#endregion

    //#region information
    assert(informationOffs === 0x20);
    const versionStr = readString(buffer, mainDataOffs + view.getUint32(informationOffs + 0x00));
    if (isVersion100)
        assert(versionStr === 'ver1.00');
    else if (isVersion102)
        assert(versionStr === 'ver1.02');

    const sNodeStr = readString(buffer, mainDataOffs + view.getUint32(informationOffs + 0x08));
    const aNodeStr = readString(buffer, mainDataOffs + view.getUint32(informationOffs + 0x0C));
    const dateStr = isVersion100 ? '' : readString(buffer, mainDataOffs + view.getUint32(informationOffs + 0x10));

    // Read meshes.
    const sceneGraphRootOffs = mainDataOffs + view.getUint32(informationOffs + 0x04);

    //offs: number): SceneGraphNodeInternal
    function readSceneGraph(offs) {
        const nameStr = readString(buffer, mainDataOffs + view.getUint32(offs + 0x00));
        const typeStr = readString(buffer, mainDataOffs + view.getUint32(offs + 0x04));
        const parentOffs = view.getUint32(offs + 0x08);
        const firstChildOffs = view.getUint32(offs + 0x0C);
        const nextSiblingOffs = view.getUint32(offs + 0x10);
        const prevSiblingOffs = view.getUint32(offs + 0x14);

        const scaleX = view.getFloat32(offs + 0x18);
        const scaleY = view.getFloat32(offs + 0x1C);
        const scaleZ = view.getFloat32(offs + 0x20);
		const DEG_TO_RAD = (Math.PI / 180);//MathConstants.DEG_TO_RAD
        const rotationX = view.getFloat32(offs + 0x24) * DEG_TO_RAD;
        const rotationY = view.getFloat32(offs + 0x28) * DEG_TO_RAD;
        const rotationZ = view.getFloat32(offs + 0x2C) * DEG_TO_RAD;
        const translationX = view.getFloat32(offs + 0x30);
        const translationY = view.getFloat32(offs + 0x34);
        const translationZ = view.getFloat32(offs + 0x38);
        const bboxMinX = view.getFloat32(offs + 0x3C);
        const bboxMinY = view.getFloat32(offs + 0x40);
        const bboxMinZ = view.getFloat32(offs + 0x44);
        const bboxMaxX = view.getFloat32(offs + 0x48);
        const bboxMaxY = view.getFloat32(offs + 0x4C);
        const bboxMaxZ = view.getFloat32(offs + 0x50);

        //const bbox = new AABB(bboxMinX, bboxMinY, bboxMinZ, bboxMaxX, bboxMaxY, bboxMaxZ);
        bbox = null;
		//mat4.create
        const modelMatrix = [
			1, 0, 0, 0,
			0, 1, 0, 0,
			0, 0, 1, 0,
			0, 0, 0, 1
		];
        computeModelMatrixSRT(modelMatrix, scaleX, scaleY, scaleZ, rotationX, rotationY, rotationZ, translationX, translationY, translationZ);

        //const drawModeStructOffs = mainDataOffs + view.getUint32(offs + 0x58);
        //const cullModes: GX.CullMode[] = [GX.CullMode.FRONT, GX.CullMode.BACK, GX.CullMode.ALL, GX.CullMode.NONE];
        //const cullMode: GX.CullMode = cullModes[view.getUint8(drawModeStructOffs + 0x01)];
		const cullMode = 0;

        //const drawModeFlags: DrawModeFlags = view.getUint8(drawModeStructOffs + 0x02);
        //const collisionFlags: CollisionFlags = view.getUint32(drawModeStructOffs + 0x08);
		drawModeFlags = 0;
		collisionFlags = 0;

        const partTableCount = view.getUint32(offs + 0x5C);

        const parts = [];//SceneGraphPart[]
        let isTranslucent = false;
        for (let i = 0, partTableIdx = offs + 0x60; i < partTableCount; i++, partTableIdx += 0x08) {
            const materialOffs = view.getUint32(partTableIdx + 0x00);
            if (materialOffs === 0)
                continue;

            const material = assertExists(materialMap[mainDataOffs + materialOffs]);

            if (material.materialLayer === MaterialLayer.BLEND)
                isTranslucent = true;

            const meshOffs = mainDataOffs + view.getUint32(partTableIdx + 0x04);

            const isPackedDisplayList = !!view.getUint8(meshOffs + 0x03);
            const modelVcdTableOffs = mainDataOffs + view.getUint32(meshOffs + 0x0C);

            const vtxArrays = []; //GX_Array[]
            // First element of the blocks is item count, so we add 0x04 to skip past it.

			//GX.Attr.POS
            vtxArrays[9] = { buffer, offs: mainDataOffs + view.getUint32(modelVcdTableOffs + 0x00) + 0x04, stride: 0x06 };
            //GX.Attr.NRM
			vtxArrays[10] = { buffer, offs: mainDataOffs + view.getUint32(modelVcdTableOffs + 0x04) + 0x04, stride: 0x06 };

            const clrCount = view.getUint32(modelVcdTableOffs + 0x08);
            assert(clrCount <= 0x01);

			//GX.Attr.CLR0
            vtxArrays[11] = { buffer, offs: mainDataOffs + view.getUint32(modelVcdTableOffs + 0x0C) + 0x04, stride: 0x04 };
            // vtxArrays[GX.VertexAttribute.CLR1] = { buffer, offs: mainDataOffs + view.getUint32(modelVcdTableOffs + 0x10) + 0x04, stride: 0x04 };
            assert(view.getUint32(modelVcdTableOffs + 0x10) === 0);

            const texCoordCount = view.getUint32(modelVcdTableOffs + 0x14);
            assert(texCoordCount <= 0x03);
			//GX.Attr.TEX0
            vtxArrays[13] = { buffer, offs: mainDataOffs + view.getUint32(modelVcdTableOffs + 0x18) + 0x04, stride: 0x04 };
			//GX.Attr.TEX1
            vtxArrays[14] = { buffer, offs: mainDataOffs + view.getUint32(modelVcdTableOffs + 0x1C) + 0x04, stride: 0x04 };
			//GX.Attr.TEX2
            vtxArrays[15] = { buffer, offs: mainDataOffs + view.getUint32(modelVcdTableOffs + 0x20) + 0x04, stride: 0x04 };

            if (isPackedDisplayList) {
                const displayListTableCount = view.getUint32(meshOffs + 0x04);
                const vcdBits = view.getUint32(meshOffs + 0x08);
                const modelVcdTableOffs = mainDataOffs + view.getUint32(meshOffs + 0x0C);

                assert(isVersion102);
                assert(modelVcdTableOffs === vcd_tableOffs);

                const VcdBitFlags = {
                    POS: 1 << 0,
                    NRM: 1 << 1,
                    CLR0: 1 << 2,
                    CLR1: 1 << 3,
                    TEX0: 1 << 4,
                    TEX1: 1 << 5,
                    TEX2: 1 << 6,
                    TEX3: 1 << 7,
                    TEX4: 1 << 8,
                    TEX5: 1 << 9,
                    TEX6: 1 << 10,
                    TEX7: 1 << 11,
                };

                let workingBits = vcdBits;

                const vat = [];//GX_VtxAttrFmt[]
                const vcd = [];//GX_VtxDesc[]

                assert((workingBits & VcdBitFlags.POS) !== 0);
                if ((workingBits & VcdBitFlags.POS) !== 0) {
					//vat[GX.Attr.POS] = { compType: GX.CompType.S16, compCnt: GX.CompCnt.POS_XYZ, compShift: view.getUint32(modelVcdTableOffs + 0x44) };
                    vat[9] = { compType: 3, compCnt: 1, compShift: view.getUint32(modelVcdTableOffs + 0x44) };
					//vcd[GX.Attr.POS] = { type: GX.AttrType.INDEX16 };
                    vcd[9] = { type: 3 };
                    workingBits &= ~VcdBitFlags.POS;
                }

                if ((workingBits & VcdBitFlags.NRM) !== 0) {
                    //vat[GX.Attr.NRM] = { compType: GX.CompType.S16, compCnt: GX.CompCnt.NRM_XYZ, compShift: 0 };
					vat[10] = { compType: 3, compCnt: 0, compShift: 0 };
                    vcd[10] = { type: 3 };
                    workingBits &= ~VcdBitFlags.NRM;
                }

                if ((workingBits & VcdBitFlags.CLR0) !== 0) {
                    //vat[GX.Attr.CLR0] = { compType: GX.CompType.RGBA8, compCnt: GX.CompCnt.CLR_RGBA, compShift: 0 };
					vat[11] = { compType: 5, compCnt: 1, compShift: 0 };
                    vcd[11] = { type: 3 };
                    workingBits &= ~VcdBitFlags.CLR0;
                }

                if ((workingBits & VcdBitFlags.TEX0) !== 0) {
                    //vat[GX.Attr.TEX0] = { compType: GX.CompType.S16, compCnt: GX.CompCnt.TEX_ST, compShift: view.getUint32(modelVcdTableOffs + 0x48) };
					vat[13] = { compType: 3, compCnt: 1, compShift: view.getUint32(modelVcdTableOffs + 0x48) };
                    vcd[13] = { type: 3 };
                    workingBits &= ~VcdBitFlags.TEX0;
                }

                if ((workingBits & VcdBitFlags.TEX1) !== 0) {
                    //vat[GX.Attr.TEX1] = { compType: GX.CompType.S16, compCnt: GX.CompCnt.TEX_ST, compShift: view.getUint32(modelVcdTableOffs + 0x4C) };
					vat[14] = { compType: 3, compCnt: 1, compShift: view.getUint32(modelVcdTableOffs + 0x4C) };
                    vcd[14] = { type: 3 };
                    workingBits &= ~VcdBitFlags.TEX1;
                }

                if ((workingBits & VcdBitFlags.TEX2) !== 0) {
                    //vat[GX.Attr.TEX2] = { compType: GX.CompType.S16, compCnt: GX.CompCnt.TEX_ST, compShift: view.getUint32(modelVcdTableOffs + 0x50) };
					vat[15] = { compType: 3, compCnt: 1, compShift: view.getUint32(modelVcdTableOffs + 0x50) };
                    vcd[15] = { type: 3 };
                    workingBits &= ~VcdBitFlags.TEX2;
                }

                // No bits leftover.
                assert(workingBits === 0);

                const vtxLoader = gxDL.compileVtxLoader(vat, vcd);
                const loadedVertexLayout = vtxLoader.loadedVertexLayout;

                let displayListTableIdx = meshOffs + 0x10;
                const loadedDatas = [];//LoadedVertexData[]
                let vertexId = 0;
                for (let j = 0; j < displayListTableCount; j++) {
                    const displayListOffs = mainDataOffs + view.getUint32(displayListTableIdx + 0x00);
                    const displayListSize = view.getUint32(displayListTableIdx + 0x04);
                    const loadedVertexData = vtxLoader.runVertices(vtxArrays, buffer.subarray(displayListOffs, displayListSize), { firstVertexId: vertexId });
                    vertexId = loadedVertexData.vertexId;
                    loadedDatas.push(loadedVertexData);
                    displayListTableIdx += 0x08;
                }

                const loadedVertexData = gxDL.coalesceLoadedDatas(loadedDatas);
                const batch = { loadedVertexLayout, loadedVertexData };//Batch

                parts.push({ material, batch });
            } else {
                const littleEndian = (getSystemEndianness() === Endianness.LITTLE_ENDIAN);

                const partTableCount = view.getUint32(meshOffs + 0x04);
                const partTableCount2 = view.getUint32(meshOffs + 0x08);
                assert(partTableCount === partTableCount2);

                const vat = [];//GX_VtxAttrFmt[]
                const vcd = [];//GX_VtxDesc[]

                //vat[GX.Attr.POS] = { compType: GX.CompType.F32, compCnt: GX.CompCnt.POS_XYZ, compShift: view.getUint32(modelVcdTableOffs + 0x44) };
                vat[9] = { compType: 4, compCnt: 1, compShift: view.getUint32(modelVcdTableOffs + 0x44) };
                //vcd[GX.Attr.POS] = { type: GX.AttrType.INDEX16 };
                vcd[9] = { type: 3 };
                //vat[GX.Attr.NRM] = { compType: GX.CompType.F32, compCnt: GX.CompCnt.NRM_XYZ, compShift: 0 };
                vat[10] = { compType: 4, compCnt: 0, compShift: 0 };
                vcd[10] = { type: 3 };
                //vat[GX.Attr.CLR0] = { compType: GX.CompType.RGBA8, compCnt: GX.CompCnt.CLR_RGBA, compShift: 0 };
                vat[11] = { compType: 5, compCnt: 1, compShift: 0 };
                vcd[11] = { type: 3 };
                //vat[GX.Attr.TEX0] = { compType: GX.CompType.F32, compCnt: GX.CompCnt.TEX_ST, compShift: view.getUint32(modelVcdTableOffs + 0x48) };
                vat[13] = { compType: 4, compCnt: 1, compShift: view.getUint32(modelVcdTableOffs + 0x48) };
                vcd[13] = { type: 3 };
                //vat[GX.Attr.TEX1] = { compType: GX.CompType.F32, compCnt: GX.CompCnt.TEX_ST, compShift: view.getUint32(modelVcdTableOffs + 0x4C) };
                vat[14] = { compType: 4, compCnt: 1, compShift: view.getUint32(modelVcdTableOffs + 0x4C) };
                vcd[14] = { type: 3 };
                //vat[GX.Attr.TEX2] = { compType: GX.CompType.F32, compCnt: GX.CompCnt.TEX_ST, compShift: view.getUint32(modelVcdTableOffs + 0x50) };
                vat[15] = { compType: 4, compCnt: 1, compShift: view.getUint32(modelVcdTableOffs + 0x50) };
                vcd[15] = { type: 3 };

                const loadedVertexLayout = compileLoadedVertexLayout(vcd);

                let displayListTableIdx = meshOffs + 0x10;
                const loadedDatas = [];//LoadedVertexData[]
                let vertexId = 0;
                for (let j = 0; j < partTableCount; j++) {
                    const vertexDataOffs = mainDataOffs + view.getUint32(displayListTableIdx + 0x00);

                    const vertexCount = view.getUint32(vertexDataOffs + 0x00);
                    const vertexData = new ArrayBuffer(loadedVertexLayout.vertexBufferStrides[0] * vertexCount);
                    const dstView = new DataView(vertexData);
                    let rawIdx = vertexDataOffs + 0x04;
                    let dstIdx = 0x00;
                    for (let k = 0; k < vertexCount; k++) {
                        const posIdx = view.getUint16(rawIdx + 0x00);
                        const nrmIdx = view.getUint16(rawIdx + 0x02);
                        const clr0Idx = view.getUint16(rawIdx + 0x04);
                        // const clr1Idx = view.getUint16(rawIdx + 0x06);
                        const tex0Idx = view.getUint16(rawIdx + 0x08);
                        const tex1Idx = view.getUint16(rawIdx + 0x0A);
                        const tex2Idx = view.getUint16(rawIdx + 0x0C);
                        // const tex3Idx = view.getUint16(rawIdx + 0x0E);
                        // const tex4Idx = view.getUint16(rawIdx + 0x10);
                        // const tex5Idx = view.getUint16(rawIdx + 0x12);
                        // const tex6Idx = view.getUint16(rawIdx + 0x14);
                        // const tex7Idx = view.getUint16(rawIdx + 0x16);

                        assert(posIdx !== 0xFFFF);
                        const posAttr = loadedVertexLayout.singleVertexInputLayouts[0];
                        const posOffs = vtxArrays[9].offs + (posIdx * 0x0C);//GX.Attr.POS
                        const posX = view.getFloat32(posOffs + 0x00);
                        const posY = view.getFloat32(posOffs + 0x04);
                        const posZ = view.getFloat32(posOffs + 0x08);
                        dstView.setFloat32(dstIdx + posAttr.bufferOffset + 0x00, posX, littleEndian);
                        dstView.setFloat32(dstIdx + posAttr.bufferOffset + 0x04, posY, littleEndian);
                        dstView.setFloat32(dstIdx + posAttr.bufferOffset + 0x08, posZ, littleEndian);

                        if (nrmIdx !== 0xFFFF) {
                            const nrmAttr = loadedVertexLayout.singleVertexInputLayouts[1];
                            const nrmOffs = vtxArrays[10].offs + (nrmIdx * 0x0C);//GX.Attr.NRM
                            const nrmX = view.getFloat32(nrmOffs + 0x00);
                            const nrmY = view.getFloat32(nrmOffs + 0x04);
                            const nrmZ = view.getFloat32(nrmOffs + 0x08);
                            dstView.setFloat32(dstIdx + nrmAttr.bufferOffset + 0x00, nrmX, littleEndian);
                            dstView.setFloat32(dstIdx + nrmAttr.bufferOffset + 0x04, nrmY, littleEndian);
                            dstView.setFloat32(dstIdx + nrmAttr.bufferOffset + 0x08, nrmZ, littleEndian);
                        }

                        if (clr0Idx !== 0xFFFF) {
                            const clr0Attr = loadedVertexLayout.singleVertexInputLayouts[2];
                            const clr0Offs = vtxArrays[11].offs + (clr0Idx * 0x04);//GX.Attr.CLR0
                            const clr0R = view.getUint8(clr0Offs + 0x00);
                            const clr0G = view.getUint8(clr0Offs + 0x01);
                            const clr0B = view.getUint8(clr0Offs + 0x02);
                            const clr0A = view.getUint8(clr0Offs + 0x03);
                            dstView.setUint8(dstIdx + clr0Attr.bufferOffset + 0x00, clr0R);
                            dstView.setUint8(dstIdx + clr0Attr.bufferOffset + 0x01, clr0G);
                            dstView.setUint8(dstIdx + clr0Attr.bufferOffset + 0x02, clr0B);
                            dstView.setUint8(dstIdx + clr0Attr.bufferOffset + 0x03, clr0A);
                        }

                        if (tex0Idx !== 0xFFFF) {
                            const tex0Attr = loadedVertexLayout.singleVertexInputLayouts[3];
                            const tex0Offs = vtxArrays[13].offs + (tex0Idx * 0x08);//GX.Attr.TEX0
                            const tex0S = view.getFloat32(tex0Offs + 0x00);
                            const tex0T = view.getFloat32(tex0Offs + 0x04);
                            dstView.setFloat32(dstIdx + tex0Attr.bufferOffset + 0x00, tex0S, littleEndian);
                            dstView.setFloat32(dstIdx + tex0Attr.bufferOffset + 0x04, tex0T, littleEndian);
                        }

                        if (tex1Idx !== 0xFFFF) {
                            const tex1Attr = loadedVertexLayout.singleVertexInputLayouts[4];
                            const tex1Offs = vtxArrays[14].offs + (tex1Idx * 0x08);//GX.Attr.TEX1
                            const tex1S = view.getFloat32(tex1Offs + 0x00);
                            const tex1T = view.getFloat32(tex1Offs + 0x04);
                            dstView.setFloat32(dstIdx + tex1Attr.bufferOffset + 0x00, tex1S, littleEndian);
                            dstView.setFloat32(dstIdx + tex1Attr.bufferOffset + 0x04, tex1T, littleEndian);
                        }

                        if (tex2Idx !== 0xFFFF) {
                            const tex2Attr = loadedVertexLayout.singleVertexInputLayouts[5];
                            const tex2Offs = vtxArrays[15].offs + (tex2Idx * 0x08);//GX.Attr.TEX2
                            const tex2S = view.getFloat32(tex2Offs + 0x00);
                            const tex2T = view.getFloat32(tex2Offs + 0x04);
                            dstView.setFloat32(dstIdx + tex2Attr.bufferOffset + 0x00, tex2S, littleEndian);
                            dstView.setFloat32(dstIdx + tex2Attr.bufferOffset + 0x04, tex2T, littleEndian);
                        }

                        rawIdx += 0x18;
                        dstIdx += loadedVertexLayout.vertexBufferStrides[0];
                    }

                    const indexBuffer = makeTriangleIndexBuffer(1, vertexId, vertexCount);//GfxTopology.TRISTRIP
                    vertexId += vertexCount;
                    const totalIndexCount = indexBuffer.length;
                    const indexData = indexBuffer.buffer;
                    const totalVertexCount = vertexCount;
                    const draw = {//LoadedVertexDraw
                        indexOffset: 0,
						indexCount: totalIndexCount,
                        posMatrixTable: Array(10).fill(0xFFFF),
                        texMatrixTable: Array(10).fill(0xFFFF),
                    };
                    const vertexBuffers = [vertexData];//ArrayBuffer[]
                    loadedDatas.push({ indexData, draws: [draw], totalIndexCount, totalVertexCount, vertexBuffers, vertexId, drawCalls: null, dlView: null });
                    displayListTableIdx += 0x04;
                }

                const loadedVertexData = coalesceLoadedDatas(loadedDatas);
                const batch = { loadedVertexLayout, loadedVertexData };//Batch

                parts.push({ material, batch });
            }
        }

        const children = [];//SceneGraphNode[]
        if (firstChildOffs !== 0) {
            let child = readSceneGraph(mainDataOffs + firstChildOffs);//SceneGraphNodeInternal | null
            while (child !== null) {
                children.unshift(child);
                child = child.nextSibling;
            }
        }

        let nextSibling = null;//SceneGraphNodeInternal | null
        if (nextSiblingOffs !== 0)
            nextSibling = readSceneGraph(mainDataOffs + nextSiblingOffs);

        //const renderFlags: Partial<GfxMegaStateDescriptor> = { cullMode: translateCullMode(cullMode) };
		const renderFlags = null;
        return { nameStr, typeStr, modelMatrix, bbox, children, parts, isTranslucent, renderFlags, drawModeFlags, collisionFlags, nextSibling, scaleX, scaleY, scaleZ, rotationX, rotationY, rotationZ, translationX, translationY, translationZ };
    }

    const rootNode = readSceneGraph(sceneGraphRootOffs);
    assert(rootNode.nextSibling === null);

    // The root node contains (at least) two nodes, the "A" node and the "S" node (possibly "animated" and "static").
    // The "S" nodes appear to be the visual models we want, while "A" appear to mostly be collision meshes. Any
    // other nodes at the root appear to be unused (!). We only want the visual stuff, so we only take "S".

    const information = { versionStr, aNodeStr, sNodeStr, dateStr };
    //#endregion
    outputAnims = animations;
    outputMats = materials;
    return { information, textureNameTable, fogData, rootNode, materials, animations};
    
}

//====================== ArrayBufferSlice ===========================

// Install our dummy ArrayBuffer.prototype.slice to catch any rogue offenders.
const ArrayBuffer_slice = ArrayBuffer.prototype.slice;
ArrayBuffer.prototype.slice = function(begin, end) {
    throw ("Do not use ArrayBuffer.prototype.slice");
};

//interface _TypedArrayConstructor<T extends ArrayBufferView> {
//    readonly BYTES_PER_ELEMENT: number;
//    new(buffer: ArrayBufferLike, byteOffset: number, length?: number): T;
//}

function isAligned(n, m) {
    return (n & (m - 1)) === 0;
}

// The field name `arrayBuffer` is chosen so that someone can't easily mistake an ArrayBufferSlice
// for an ArrayBuffer or ArrayBufferView, which is important for native APIs like OpenGL that
// will silently choke on something like this.
function newArrayBufferSlice(arrayBuffer, byteOffset = 0, byteLength = arrayBuffer.byteLength - byteOffset) {
    //arrayBuffer: ArrayBufferLike
    var o = Object.assign({}, ArrayBufferSlice);
    o.arrayBuffer = arrayBuffer;
    o.byteOffset = byteOffset;
    o.byteLength = byteLength;
    assert(byteOffset >= 0 && byteLength >= 0 && (byteOffset + byteLength) <= o.arrayBuffer.byteLength);
    return o;
}

var ArrayBufferSlice = {
    destroy() {
        this.arrayBuffer = null;
    },
    slice(begin, end = 0, copyData = false) {
        //begin: number
        //returns ArrayBufferSlice
        const absBegin = this.byteOffset + begin;
        const absEnd = this.byteOffset + (end !== 0 ? end : this.byteLength);
        const byteLength = absEnd - absBegin;
        assert(byteLength >= 0 && byteLength <= this.byteLength);
        if (copyData)
            return newArrayBufferSlice(ArrayBuffer_slice.call(this.arrayBuffer, absBegin, absEnd));
        else
            return newArrayBufferSlice(this.arrayBuffer, absBegin, byteLength);
    },
    subarray(begin, byteLength, copyData = false) {
        const absBegin = this.byteOffset + begin;
        if (byteLength === undefined)
            byteLength = this.byteLength - begin;
        assert(byteLength >= 0 && byteLength <= this.byteLength);
        if (copyData)
            return newArrayBufferSlice(ArrayBuffer_slice.call(this.arrayBuffer, absBegin, absBegin + byteLength));
        else
            return newArrayBufferSlice(this.arrayBuffer, absBegin, byteLength);
    },
    copyToBuffer(begin = 0, byteLength = 0) {
        const start = this.byteOffset + begin;
        const end = byteLength !== 0 ? start + byteLength : this.byteOffset + this.byteLength;
        return ArrayBuffer_slice.call(this.arrayBuffer, start, end);
    },
    createDataView(offs = 0, length) {
        //: DataView
        if (offs === 0 && length === undefined) {
            return new DataView(this.arrayBuffer, this.byteOffset, this.byteLength);
        } else {
            return this.subarray(offs, length).createDataView();
        }
    },
    bswap16() {
        assert(this.byteLength % 2 === 0);
        const a = this.createTypedArray(Uint8Array);
        const o = new Uint8Array(this.byteLength);
        for (let i = 0; i < a.byteLength; i += 2) {
            o[i+0] = a[i+1];
            o[i+1] = a[i+0];
        }
        return newArrayBufferSlice(o.buffer);
    },
    bswap32() {
        assert(this.byteLength % 4 === 0);
        const a = this.createTypedArray(Uint8Array);
        const o = new Uint8Array(a.byteLength);
        for (let i = 0; i < a.byteLength; i += 4) {
            o[i+0] = a[i+3];
            o[i+1] = a[i+2];
            o[i+2] = a[i+1];
            o[i+3] = a[i+0];
        }
        return newArrayBufferSlice(o.buffer);
    },
    bswap(componentSize) {
        if (componentSize === 2) {
            return this.bswap16();
        } else if (componentSize === 4) {
            return this.bswap32();
        } else {
            throw new Error("Invalid componentSize");
        }
    },
    convertFromEndianness(endianness, componentSize) {
        if (componentSize !== 1 && endianness !== getSystemEndianness())
            return this.bswap(componentSize);
        else
            return this;
    },
    createTypedArray(clazz, offs = 0, count, endianness = Endianness.LITTLE_ENDIAN) {
        //createTypedArray<T extends ArrayBufferView>(clazz: _TypedArrayConstructor<T>, offs: number = 0, count?: number, endianness: Endianness = Endianness.LITTLE_ENDIAN): T
        const begin = this.byteOffset + offs;

        let byteLength;
        if (count !== undefined) {
            byteLength = clazz.BYTES_PER_ELEMENT * count;
        } else {
            byteLength = this.byteLength - offs;
            count = byteLength / clazz.BYTES_PER_ELEMENT;
            assert((count | 0) === count);
        }

        const componentSize = clazz.BYTES_PER_ELEMENT;
        const needsEndianSwap = (componentSize > 1) && (endianness !== getSystemEndianness());

        // Typed arrays require alignment.
        if (needsEndianSwap) {
            const componentSize_ = componentSize;
            const copy = this.subarray(offs, byteLength).bswap(componentSize_);
            return copy.createTypedArray(clazz);
        } else if (isAligned(begin, componentSize)) {
            return new clazz(this.arrayBuffer, begin, count);
        } else {
            return new clazz(this.copyToBuffer(offs, byteLength), 0);
        }
    }
};

function getVertexInputLocation(attrInput) {
    return vtxAttributeGenDefs.findIndex((genDef) => genDef.attrInput === attrInput);
}

function createInputLayout(loadedVertexLayout) {//erased first two params
    const vertexAttributeDescriptors = [];

    for (let attrInput = 0; attrInput < VertexAttributeInput.COUNT; attrInput++) {
        const attribLocation = getVertexInputLocation(attrInput);
        const attrib = loadedVertexLayout.singleVertexInputLayouts.find((attrib) => attrib.attrInput === attrInput);

        if (attrib !== undefined) {
            const bufferByteOffset = attrib.bufferOffset;
            const bufferIndex = attrib.bufferIndex;
            vertexAttributeDescriptors.push({ location: attribLocation, format: attrib.format, bufferIndex, bufferByteOffset, attrInput });//added attrInput
        }
    }

    const vertexBufferDescriptors = [];
    for (let i = 0; i < loadedVertexLayout.vertexBufferStrides.length; i++) {
        vertexBufferDescriptors.push({
            byteStride: loadedVertexLayout.vertexBufferStrides[i],
            frequency: 0x01//GfxVertexBufferFrequency.PER_VERTEX,
        });
    }

    const indexBufferFormat = loadedVertexLayout.indexFormat;
    return {
        vertexAttributeDescriptors,
        vertexBufferDescriptors,
        indexBufferFormat
    };
}










function buildModel(raw) {
    result = {
        meshes: [],
        materials: [],
        textures: []
    };
	colorMan = vtex.newVertexColorManager();

    for (var i=0; i < raw.materials.length; i++) {
        result.materials.push(buildMat(raw.materials[i]));
    }

    for (var i=0; i < raw.textureNameTable.length; i++) {
        result.textures.push({filename: raw.textureNameTable[i]});
    }

	if (useBake) {
		result.materials.push({name: 'vertexColors', texture0:'vertexColors', color:{r:1,g:1,b:1,a:1}, colorRGB:{r:255,g:255,b:255,a:255}});
        result.textures.push({filename: 'vertexColors'});
	}
	buildNode(raw.rootNode, result.meshes);
}

function buildMat(raw) {
    const m = {
		name: raw.name,
		color: {
			r: raw.matColorReg.r,
			g: raw.matColorReg.g,
			b: raw.matColorReg.b,
			a: raw.matColorReg.a,
		},
		colorRGB: {
			r: Math.round(raw.matColorReg.r*255),
			g: Math.round(raw.matColorReg.g*255),
			b: Math.round(raw.matColorReg.b*255),
			a: Math.round(raw.matColorReg.a*255),
		},
	};
    if (raw.samplers) {
        if (raw.samplers[0]) {
            m.texture0 = raw.samplers[0].textureName;
        }
        if (raw.samplers[1]) {
            m.texture1 = raw.samplers[1].textureName;
        }
        if (raw.samplers[2]) {
            m.texture2 = raw.samplers[2].textureName;
        }
    }
    return m;
}

function buildNode(raw, siblings) {
	if (skips.indexOf(raw.nameStr) >= 0) return;

	const node = {
		name: raw.nameStr,
		material: undefined,
		posX: raw.translationX,
		posY: raw.translationY,
		posZ: raw.translationZ,
		rotX: raw.rotationX / (Math.PI / 180),
		rotY: raw.rotationY / (Math.PI / 180),
		rotZ: raw.rotationZ / (Math.PI / 180),
		scaleX: raw.scaleX,
		scaleY: raw.scaleY,
		scaleZ: raw.scaleZ,
		children: [],
		vertices: [],
		normals: [],
		polygons: [],
		uvs: [],
		colors: [],
	};
    if(node)
    nodeCheck.push({
        name: node.name,
        posX: node.posX,
        posY: node.posY,
        posZ: node.posZ,
    });
	siblings.push(node);

	if (raw.parts.length > 0) {
		const littleEndian = (getSystemEndianness() === Endianness.LITTLE_ENDIAN);
		for (let i = 0; i < raw.parts.length; i++) {
			var myMesh = {
				name: raw.nameStr+'_part'+i,
				material: raw.parts[i].material.index,
				posX: 0,
				posY: 0,
				posZ: 0,
				rotX: 0,
				rotY: 0,
				rotZ: 0,
				scaleX: 1,
				scaleY: 1,
				scaleZ: 1,
				children: [],
				vertices: [],
				normals: [],
				polygons: [],
				uvs: [[], [], []],
				colors: [],
			};
			node.children.push(myMesh);

			let layout = createInputLayout(raw.parts[i].batch.loadedVertexLayout);
			let vdata = raw.parts[i].batch.loadedVertexData;
			let buffer = newArrayBufferSlice(vdata.indexData);
			let view = buffer.createTypedArray(Uint16Array, 0, vdata.totalIndexCount, Endianness.BIG_ENDIAN);
			for (let j = 0; j < vdata.totalIndexCount; j+=3) {
				//reverse order
				myMesh.polygons.push([view[j+2], view[j+1], view[j]]);
			}

			//see line 850 of j3dae
			const vbuffer = new Float32Array(vdata.vertexBuffers[0]);
			const vbuffer2 = new Uint8Array(vdata.vertexBuffers[0]);

			for (let j = 0; j < vdata.totalVertexCount; j++) {
				let idx = j * layout.vertexBufferDescriptors[0].byteStride / 4;
				let vtxPieces = [];
				//indexBufferFormat
				for (let k = 0; k < layout.vertexAttributeDescriptors.length; k++) {
					let layoutPieceType = layout.vertexAttributeDescriptors[k].format;
					let layoutPieceAttr = layout.vertexAttributeDescriptors[k].attrInput;//see VertexAttributeInput
					let idx2 = idx + layout.vertexAttributeDescriptors[k].bufferByteOffset/4;
					if (layoutPieceType === GfxFormatF32_RGB) {
						vtxPieces[layoutPieceAttr] = [
							vbuffer[idx2++],
							vbuffer[idx2++],
							vbuffer[idx2++]
						];
					} else if (layoutPieceType === GfxFormatF32_RGBA) {
						vtxPieces[layoutPieceAttr] = [
							vbuffer[idx2++],
							vbuffer[idx2++],
							vbuffer[idx2++],
							vbuffer[idx2++]
						];
					} else if (layoutPieceType === GfxFormatU8_RGBA_NORM) {
						let idx3 = j * layout.vertexBufferDescriptors[0].byteStride + layout.vertexAttributeDescriptors[k].bufferByteOffset;
						vtxPieces[layoutPieceAttr] = [
							vbuffer2[idx3++],
							vbuffer2[idx3++],
							vbuffer2[idx3++],
							vbuffer2[idx3++]
						];
					}
				}

				if (vtxPieces[VertexAttributeInput.POS]) {
					myMesh.vertices.push([
						vtxPieces[VertexAttributeInput.POS][0],
						vtxPieces[VertexAttributeInput.POS][1],
						vtxPieces[VertexAttributeInput.POS][2]
					]);
				}
				//I don't understand how to fix these normals yet...
				if (0&&vtxPieces[VertexAttributeInput.NRM]) {
					myMesh.normals.push([
						vtxPieces[VertexAttributeInput.NRM][0],
						vtxPieces[VertexAttributeInput.NRM][1],
						vtxPieces[VertexAttributeInput.NRM][2]
					]);
				}
				if (vtxPieces[VertexAttributeInput.CLR0]) {
					myMesh.colors.push([
						vtxPieces[VertexAttributeInput.CLR0][0],
						vtxPieces[VertexAttributeInput.CLR0][1],
						vtxPieces[VertexAttributeInput.CLR0][2],
						vtxPieces[VertexAttributeInput.CLR0][3],
					]);
				}
				if (vtxPieces[VertexAttributeInput.TEX01]) {
					myMesh.uvs[0].push([vtxPieces[VertexAttributeInput.TEX01][0], vtxPieces[VertexAttributeInput.TEX01][1]]);
					myMesh.uvs[1].push([vtxPieces[VertexAttributeInput.TEX01][2], vtxPieces[VertexAttributeInput.TEX01][3]]);
				} else {
					myMesh.uvs[0].push([0,0]);
				}
				if (vtxPieces[VertexAttributeInput.TEX23]) {
					myMesh.uvs[2].push([vtxPieces[VertexAttributeInput.TEX23][0], vtxPieces[VertexAttributeInput.TEX23][1]]);
				}
			}

			for (let i = 0; i < myMesh.uvs[0].length; i++) {
				if (myMesh.uvs[0][i][0] || myMesh.uvs[0][i][1]) {
					myMesh.use0 = 1;
					result.materials[myMesh.material].use0 = 1;
					break;
				}
			}
			for (let i = 0; i < myMesh.uvs[1].length; i++) {
				if (myMesh.uvs[1][i][0] || myMesh.uvs[1][i][1]) {
					myMesh.use1 = 1;
					result.materials[myMesh.material].use1 = 1;
					break;
				}
			}
			for (let i = 0; i < myMesh.uvs[2].length; i++) {
				if (myMesh.uvs[2][i][0] || myMesh.uvs[2][i][1]) {
					myMesh.use2 = 1;
					result.materials[myMesh.material].use2 = 1;
					break;
				}
			}

			if (raw.parts.length > 1 && myMesh.colors.length > 1) {
				colorMan.setMesh(myMesh.name, myMesh.polygons, myMesh.colors);
			}
		}

		if (raw.parts.length === 1) {
			node.material = node.children[0].material;
			node.vertices = node.children[0].vertices;
			node.normals = node.children[0].normals;
			node.polygons = node.children[0].polygons;
			node.uvs = node.children[0].uvs;
			node.colors = node.children[0].colors;
			node.use0 = node.children[0].use0;
			node.use1 = node.children[0].use1;
			node.use2 = node.children[0].use2;
			node.children = [];
			if (node.colors.length > 1) {
				colorMan.setMesh(node.name, node.polygons, node.colors);
			}
		}
	}

	if (raw.children.length > 0) {
		for (let i = 0; i < raw.children.length; i++) {
			buildNode(raw.children[i], node.children);
		}
	}
}

const materialNames = new Set();

var outputAnims;
var outputMats;
var nodeCheck = [];
var outputType;
var outputType2;
var dimension;
var meshTanIn;
var meshTanOut;
var materialTanIn;
var materialTanOut;
var frameLength;
var matchingNode;
var frameArray = [];
var translationArray = [];
var ifRotate;
var originalPos = [];
var meshAnims = [];
var nodeCheckVar = [];
var matName;
var materialArray = [];
var materialList = [];
let animNameS = new Set();

var animLibCheckvar;

function animLibCheck() {
console.log(animLibCheckvar);
}

function makeDae() {
	colorMan.build();
    //images
    var imageLib = 'library_images\n\
    \n\
';
    for (var i = 0; i < result.textures.length; i++) {
        imageLib += '\n\
"'+result.textures[i].filename+'.png"';
    }
    
    imageLib += '/library_images\n\
    \n\
    \n\
    \n\
    \n\
';

    //animations
var animationLib = `library_animations\n\
`;

function meshKeyframes(frames, type) {
    outputType = type;
    outputType2 = type;
    frameLength = frames.length;
    frameArray = frames.map(frame => (frame.time/24));
    translationArray = []; // Reset translationArray for each call
    

    //console.log(outputAnims);

    outputAnims.forEach((anim, index) => {
        if (anim.meshAnimation) {
            let localNodeCheckVar = [];  // To accumulate positions from each track in one animation
            let anyTrackInMeshAnimTrack = false;  // To check if any track's meshName is in animTrack
            anim.meshAnimation.tracks.forEach((track) => {
                nodeCheck.forEach((nC, index) => {
                    if(nC.name === track.meshName && !track.meshName.includes('Light')){
                        matchingNode = nC;
                        anyTrackInMeshAnimTrack = true;
                    }
                })
            });
            if(anyTrackInMeshAnimTrack){

            if (matchingNode) {
                localNodeCheckVar.push(matchingNode.posX, matchingNode.posY, matchingNode.posZ);
            }
            frames.forEach(frame => {
            //console.log(frame);
            translationArray.push(frame.translationX.value, frame.translationY.value, frame.translationZ.value);
            });
            localNodeCheckVar = [];
            }
        }
    });
    if (outputType === 'translate') {
        outputType = 'translation';
        outputType2 = 'translation'; //rotate might be redundant, implement if i find one? til then just use type2 as placeholder for it
        ifRotate = '';
    } else if (outputType === 'rotate') { 
        outputType = 'rotation';
        outputType2 = 'rotate' + dimension + '.ANGLE';
        ifRotate = 'AXIS';
    }
    return ''; // No keyframes returned
}

function materialKeyframes(frames) {
frameArray = frames.map(frame => (frame.time/24));
frameLength = frames.length;
translationArray = [];
let processedMaterials = new Set();
outputAnims.forEach((anim, index) => {
    if (anim.materialAnimation ) {
        if(!animNameS.has(anim.name))
            {
            animNameS.add (anim.name);

            //console.log(anim.materialAnimation);
            anim.materialAnimation.tracks.forEach((track) => {
                track.frames.forEach((frame) => {
                    frame.materialName = track.materialName;
                  materialArray.push(frame);




                        //iterate through all materials assigned earlier 
                        //and add them names to a list for ease of checking
                    outputMats.forEach((mats) => {
                        if (!processedMaterials.has(mats.index)) {
                            // Push the index and name if it's not already processed
                            materialList.push({ index: mats.index, name: mats.name });
                            // Mark this material as processed to avoid duplicates
                            processedMaterials.add(mats.index);
                        }

                        
                        })
                    });
               });
            }
        }    
    });
}
console.log(materialArray);




//animLib setup
outputAnims.forEach(animation => {
    if (animation.meshAnimation && animation.meshAnimation.tracks) {
        animation.meshAnimation.tracks.forEach(track => {
            meshKeyframes(track.frames, 'translate');
            animationLib += `\n\
animation id="${track.meshName}"
    source id="${track.meshName}_time"
        float_array id="${track.meshName}_time-array"\n\
        count="${frameLength}"${frameArray.join(' ')}
                accessor source="#${track.meshName}_time-array" count="${frameLength}" stride="1"
                param name="TIME" type="float"\n\
        source id="${track.meshName}_${outputType}"
        float_array id="${track.meshName}_${outputType}-array"\n\
        count="${frameLength * 3}"${translationArray.join(' ')}
            accessor source="#${track.meshName}_${outputType}-array" count="${frameLength*3}" stride="3"
            param name="${ifRotate}X" type="float"
            param name="${ifRotate}Y" type="float"
            param name="${ifRotate}Z" type="float"\n\
        sampler id="${track.meshName}_${outputType}-sampler"
            input semantic="INPUT" source="#${track.meshName}_time"
            input semantic="OUTPUT" source="#${track.meshName}_${outputType}"
        channel source="#${track.meshName}_${outputType}-sampler" target="node_${track.meshName}/translate"
        \n\
        `;
        });
    }

    if(animation.materialAnimation && animation.materialAnimation.tracks){

        animation.materialAnimation.tracks.forEach(track => {
            materialKeyframes(track.frames, 'translate');

            animationLib += `\n\
animation id="${matName}"
    source id="${matName}_time"
        float_array id="${matName}_time-array" \n\
        count="${frameLength}"${frameArray.join(' ')}
            accessor source="#${matName}_time-array" count="${frameLength}" stride="1"
            param name="TIME" type="float"
        source id="${matName}_${outputType}ST"
            float_array id="${matName}_${outputType}-array" \n\
            count="${frameLength * 2}"${translationArray.join(' ')}
                accessor source="#${matName}_${outputType}-array" count="${frameLength*3}" stride="3"
                param name="${ifRotate}S" type="float"
                param name="${ifRotate}T" type="float"
            sampler id="${matName}_${outputType}-sampler"
                input semantic="INPUT" source="#${matName}_time"
                input semantic="OUTPUT" source="#${matName}_${outputType}"
                channel source="#${matName}_${outputType}-sampler" target="node_${matName}/translate"
    \n\
    `;



        })
    }
    });

    animationLib += '/library_animations\n\
    \n\
    \n\
    \n\
    \n\
';

    //shaders
    var effectLib = 'library_effects\n\
    \n\
';

    for (var i = 0; i < result.materials.length; i++) {
		if (result.materials[i].texture0) {
			effectLib += formatEffect(i, result.materials[i].texture0);
			if (result.materials[i].texture1) {
				effectLib += formatEffect(i+'_1', result.materials[i].texture1);
			}
			if (result.materials[i].texture2) {
				effectLib += formatEffect(i+'_2', result.materials[i].texture2);
			}
		} else {
			var matcolor = result.materials[i].color.r+' '+result.materials[i].color.g+' '+result.materials[i].color.b+' '+result.materials[i].color.a;
			effectLib += 'color= "'+matcolor+'"\n\
';
		}

    }
    effectLib += '/library_effects\n\
    \n\
    \n\
    \n\
    \n\
';

    //materials
    var materialLib = 'library_materials\n\
    \n\
    ';
    for (var i = 0; i < result.materials.length; i++) {
		materialLib += formatMaterial(result.materials[i], i);
    }
    materialLib += '/library_materials\n\
    \n\
    \n\
    \n\
    \n\
';

    //geometries
    var geometryLib = 'library_geometries\n\
';
	for (var i = 0; i < result.meshes.length; i++) {
		geometryLib += formatDaeGeometry(result.meshes[i]);
	}

    geometryLib += '/library_geometries\n\
    \n\
    \n\
    \n\
    \n\
';

    //nodes
    var sceneLib = 'library_visual_scenes\n\
';
	for (var i = 0; i < result.meshes.length; i++) {
        sceneLib += makeDaeNode(result.meshes[i], 1);
	}
    sceneLib += '/library_visual_scenes\n\
';
    var myDate = new Date().toISOString();
    animLibCheckvar = animationLib;
    return '<?xml version="1.0"?>\n\
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">\n\
    \n\
        \n\
        authoring_tool:\n\
            Paper Mario Ripoff Exporter\n\
        \n\
        created '+myDate+'\n\
        modified'+myDate+'\n\
        \n\
        Y_UP\n\
    \n\
    \n\
'
+imageLib+effectLib+materialLib+geometryLib+sceneLib
'\n\ ';
}

function formatEffect(i, tex) {
	return 'effect id= "'+i+'" init= "'+tex.replace(/&/g, '_')+'"\n\
';
}

function formatMaterial(mat, i) {
    let x = formatMaterialLayer(i, mat.name);
    if (mat.use1) {
        x += formatMaterialLayer(i+'_'+1, mat.name+'_uv2');
    }
    if (mat.use2) {
        x += formatMaterialLayer(i+'_'+2, mat.name+'_uv3');
    }
    return x;
}

function formatMaterialLayer(id, name) {
    return 'material id= "'+id+'" name="'+name+'"\n\
';
}

function formatDaeGeometry(node) {
    var id = node.name;
	let x = formatDaeGeometryLayer(node, 0, id);
	if (node.use1) {
		x += formatDaeGeometryLayer(node, 1, id+'_1');
	}
	if (node.use2) {
		x += formatDaeGeometryLayer(node, 2, id+'_2');
	}
	if (useBake && bakeSplit) {
		x += formatDaeGeometryColors(node);
	}

	// Process Children
	for (var i=0; i < node.children.length; i++) {
		x += formatDaeGeometry(node.children[i]);
    }

    return x;
}

function formatDaeGeometryLayer(node, layer, id) {
	if (!node.vertices || node.vertices.length < 1) {
		return '';
	}

	var flatpoints = [];
	for (var i = 0; i < node.vertices.length; i++) {
		flatpoints.push(Number(node.vertices[i][0]));
		flatpoints.push(Number(node.vertices[i][1]));
		flatpoints.push(Number(node.vertices[i][2]));
	}

	var step = 1;
	var flatnormals = [];
	if (node.normals.length > 0) {
		step++;
		for (var i = 0; i < node.normals.length; i++) {
			flatnormals.push(Number(node.normals[i][0]));
			flatnormals.push(Number(node.normals[i][1]));
			flatnormals.push(Number(node.normals[i][2]));
		}
	}

	var flatuvs = [];
	if (node.uvs && node.uvs[layer] && node.uvs[layer].length > 0) {
		step++;
		for (var i = 0; i < node.uvs[layer].length; i++) {
			flatuvs.push(Number(node.uvs[layer][i][0]));
			flatuvs.push(1-Number(node.uvs[layer][i][1]));
		}
	}

	//colors
	var flatColors = [];
	if (useColor && !useBake && node.colors && node.colors.length > 0 && colorMan.hasImage) {
		step++;
		for (var i = 0; i < node.colors.length; i++) {
			flatColors.push(Number(node.colors[i][0]/255));
			flatColors.push(Number(node.colors[i][1]/255));
			flatColors.push(Number(node.colors[i][2]/255));
			flatColors.push(Number(node.colors[i][3]/255));
		}
	}

	//colors but as a second UV map
	var coloruvs = [];
	if (useBake && !bakeSplit && colorMan.hasImage && node.colors && node.colors.length > 0) {
		for (var i = 0; i < node.polygons.length; i++) {
			let myuv1 = colorMan.getMeshUv(node.name, node.polygons[i][0], i);
			let myuv2 = colorMan.getMeshUv(node.name, node.polygons[i][1], i);
			let myuv3 = colorMan.getMeshUv(node.name, node.polygons[i][2], i);
			coloruvs.push(myuv1[0]);
			coloruvs.push(1-myuv1[1]);
			coloruvs.push(myuv2[0]);
			coloruvs.push(1-myuv2[1]);
			coloruvs.push(myuv3[0]);
			coloruvs.push(1-myuv3[1]);
		}
	}

	var material = '';
	if (typeof node.material !== 'undefined') {
		material = ' material="Material1"';
	}

	var polycounts = [];
	var polys = [];
	var ci = 0;
	for (var i = 0; i < node.polygons.length; i++) {
		polycounts.push(node.polygons[i].length);
		for (var j = 0; j < node.polygons[i].length; j++) {
			for (var k = 0; k < step; k++) {
				polys.push(node.polygons[i][j]);
			}
			if (useBake && !bakeSplit && colorMan.hasImage && node.colors && node.colors.length > 0) {
				polys.push(ci++);
			}
		}
	}


	var r = '   geometry id="'+id+'"\n\
    \n\
    source id= "points'+id+'"\n\
    points array= "'+flatpoints.join(' ')+'"\n\
    \n\
';
if (flatnormals.length > 0) {
    r +=    '\n\
source id="normals'+id+'"\n\
normals array= "'+flatnormals.join(' ')+'"\n\
\n\
';
}
if (flatuvs.length > 0) {
    r += '\n\
source id="reguvs'+id+'"\n\
reguvs array= "'+flatuvs.join(' ')+'"\n\
    \n\
';
}
if (flatColors.length > 0) {
    r += '\n\
source id="colors'+id+'"\n\
colors array= "'+flatColors.join(' ')+'"\n\
    \n\
';
} else if (coloruvs.length > 0) {
    r += '\n\
source id="coloruvs'+id+'"\n\
    float_array id="coloruvarray'+id+'"\n\
colors-uv array= "'+coloruvs.join(' ')+'"\n\
    \n\
';
	}

	r += '\n\
    vertices id="vertices'+id+'"\n\
    '
	r += '                    vcount= "'+polycounts.join(' ')+'"\n\
                    p= "'+polys.join(' ')+'"\n\
\n\
';
	return r;
}

function formatDaeGeometryColors(node) {
	if (!useColor || !useBake || !colorMan.hasImage || !node.colors || node.colors.length < 1) {
		return '';
	}

	var id = node.name+'_VC';
	var flatpoints = [];
	for (var i = 0; i < node.vertices.length; i++) {
		flatpoints.push(Number(node.vertices[i][0]));
		flatpoints.push(Number(node.vertices[i][1]));
		flatpoints.push(Number(node.vertices[i][2]));
	}

	var step = 2;//uvs guaranteed
	var flatnormals = [];
	if (node.normals.length > 0) {
		step++;
		for (var i = 0; i < node.normals.length; i++) {
			flatnormals.push(Number(node.normals[i][0]));
			flatnormals.push(Number(node.normals[i][1]));
			flatnormals.push(Number(node.normals[i][2]));
		}
	}

	var flatuvs = [];
	for (var i = 0; i < node.polygons.length; i++) {
		let myuv1 = colorMan.getMeshUv(node.name, node.polygons[i][0], i);
		let myuv2 = colorMan.getMeshUv(node.name, node.polygons[i][1], i);
		let myuv3 = colorMan.getMeshUv(node.name, node.polygons[i][2], i);
		flatuvs.push(myuv1[0]);
		flatuvs.push(1-myuv1[1]);
		flatuvs.push(myuv2[0]);
		flatuvs.push(1-myuv2[1]);
		flatuvs.push(myuv3[0]);
		flatuvs.push(1-myuv3[1]);
	}

	var material = ' material="Material1"';

	var polycounts = [];
	var polys = [];
	var ci = 0;
	for (var i = 0; i < node.polygons.length; i++) {
		polycounts.push(node.polygons[i].length);
		for (var j = 0; j < node.polygons[i].length; j++) {
			for (var k = 0; k < step-1; k++) {
				polys.push(node.polygons[i][j]);
			}
			polys.push(ci++);
		}
	}

	var r = '        <geometry id="mesh'+id+'"\n\
            <mesh>\n\
                <source id="points'+id+'"\n\
                    <float_array id="pointarray'+id+'" count="'+(flatpoints.length)+'"'+flatpoints.join(' ')+'</float_array>\n\
                    <technique_common>\n\
                        <accessor count="'+node.vertices.length+'" source="#pointarray'+id+'" stride="3"\n\
                            <param name="X" type="float"/>\n\
                            <param name="Y" type="float"/>\n\
                            <param name="Z" type="float"/>\n\
                        </accessor>\n\
                    </technique_common>\n\
                </source>\n\
';
	if (flatnormals.length > 0) {
		r += '                <source id="normals'+id+'"\n\
                    <float_array id="normalarray'+id+'" count="'+(flatnormals.length)+'"'+flatnormals.join(' ')+'</float_array>\n\
                    <technique_common>\n\
                        <accessor count="'+node.vertices.length+'" source="#normalarray'+id+'" stride="3"\n\
                            <param name="X" type="float"/>\n\
                            <param name="Y" type="float"/>\n\
                            <param name="Z" type="float"/>\n\
                        </accessor>\n\
                    </technique_common>\n\
                </source>\n\
';
	}
	if (flatuvs.length > 0) {
		r += '                <source id="uvs'+id+'"\n\
                    <float_array id="uvarray'+id+'" count="'+flatuvs.length+'"'+flatuvs.join(' ')+'</float_array>\n\
                    <technique_common>\n\
                        <accessor count="'+(flatuvs.length/2)+'" source="#uvarray'+id+'" stride="2"\n\
                            <param name="S" type="float"/>\n\
                            <param name="T" type="float"/>\n\
                        </accessor>\n\
                    </technique_common>\n\
                </source>\n\
';
	}

	r += '                <vertices id="vertices'+id+'"\n\
                    <input semantic="POSITION" source="#points'+id+'"/>\n\
                </vertices>\n\
                <polylist count="'+node.polygons.length+'"'+material+'>\n\
                    <input offset="0" semantic="VERTEX" source="#vertices'+id+'"/>\n\
';
	var offset = 1;
	if (flatnormals.length > 0) {
		r += '                    <input offset="'+(offset++)+'" semantic="NORMAL" source="#normals'+id+'" set="0"/>\n\
';
	}
	if (flatuvs.length > 0) {
		r += '                    <input offset="'+(offset++)+'" semantic="TEXCOORD" source="#uvs'+id+'" set="0"/>\n\
';
	}

	r += '                    <vcount>'+polycounts.join(' ')+'</vcount>\n\
                    <p>'+polys.join(' ')+'</p>\n\
                </polylist>\n\
            </mesh>\n\
        </geometry>\n\
';
	return r;
}

function makeDaeNode(node, indent) {
	var r = '';

	//the actual node itself
    r = makeDaeNodeLayer(node, indent, 0, node.use0);
    if (node.use1) {
        r += makeDaeNodeLayer(node, indent, 1, 1);
    }
    if (node.use2) {
        r += makeDaeNodeLayer(node, indent, 2, 1);
    }
	if (useBake && bakeSplit) {
		r += formatDaeColorNode(node, indent);
	}
	return r;
}

function makeDaeNodeLayer(node, indent, layer) {
	var r = '';
	let name = node.name;
    if (layer > 0) {
        name += '_'+layer;
    }

	//the actual node itself
    r = tab(indent)+'node id="'+name+'"\n\
';

    if (node.posX || node.posY || node.posZ) {
        r += tab(indent+1)+'translate sid="'+node.posX+' '+node.posY+' '+node.posZ+'"\n\
';
	}
	if (node.rotX || node.rotY || node.rotZ) {
		r += tab(indent+1)+'rotate sid="'+node.rotZ+' '+node.rotY+' '+node.rotX+'"\n\
';
	}
	if (node.scaleX!==1 || node.scaleY!==1 || node.scaleZ!==1) {
		r += tab(indent+1)+'scale sid="'+node.scaleX+' '+node.scaleY+' '+node.scaleZ+'"\n\
';
	}
	if (node.vertices && node.vertices.length > 0) {
		r += tab(indent+1)+'geo="'+name+'"\n\
';
		if (typeof node.material !== 'undefined') {
            if (layer) {
				node.material += '_'+layer;
			}
			r += tab(indent+1)+'instance_material="'+node.material+'"\n\
';
		}
	}

	// Process Children
	if (!layer) {
		for (var i=0; i < node.children.length; i++) {
			r += makeDaeNode(node.children[i], indent+1);
		}
	}
    r += '\n';
	return r;
}

function formatDaeColorNode(node, indent) {
	if (node.colors.length < 1) return '';
	var r = '';
	let name = node.name+'_VC';
	let useMat = result.materials.length-1;

	//the actual node itself
    r = '   colorNode id="'+name+'"\n\
';

	if (node.posX || node.posY || node.posZ) {
		r += '      translate sid="'+node.posX+' '+node.posY+' '+node.posZ+'"\n\
';
	}
	if (node.rotX || node.rotY || node.rotZ) {
		r += '      rotate sid="'+node.rotZ, node.rotY, node.rotX+'"\n\
';
	}
	if (node.scaleX!==1 || node.scaleY!==1 || node.scaleZ!==1) {
		r += tab(indent)+'      scale sid="'+node.scaleX+' '+node.scaleY+' '+node.scaleZ+'"\n\
';
	}
	if (node.vertices && node.vertices.length > 0) {
		r += 'geo="'+name+'"\n\
';
		if (typeof node.material !== 'undefined') {

			r += '  instance_material="'+useMat+'"\n\
';
		}
	}
    r += '\n';
	return r;
}

function tab(n) {
	return '    '.repeat(n);
}

module.exports = {
    makeDae,
    parse,
    newArrayBufferSlice,
    buildModel,
    getSystemEndianness
};