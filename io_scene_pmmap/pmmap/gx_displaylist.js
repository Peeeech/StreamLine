const GfxFormatU8_RGBA = makeFormat(0x01, 0x04, 0b00000000);// = 66560
const GfxFormatU8_RGBA_NORM = makeFormat(0x01, 0x04, 0b00000001);// = 66561
const GfxFormatU16_R = makeFormat(0x02, 0x01, 0b00000000);// = 131328
const GfxFormatF32_R = makeFormat(0x08, 0x01, 0b00000000);// = ?
const GfxFormatF32_RG = makeFormat(0x08, 0x02, 0b00000000);// = 524800
const GfxFormatF32_RGB = makeFormat(0x08, 0x03, 0b00000000);// = 525056
const GfxFormatF32_RGBA = makeFormat(0x08, 0x04, 0b00000000);// = 525312

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

//====================== Endian =====================================
const Endianness = {0: 'LITTLE_ENDIAN', 1: 'BIG_ENDIAN'}

const test = new Uint16Array([0xFEFF]);
const testView = new DataView(test.buffer);
const systemEndianness = (testView.getUint8(0) == 0xFF) ? Endianness.LITTLE_ENDIAN : Endianness.BIG_ENDIAN;

function getSystemEndianness() {
    return systemEndianness;
}

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

function fallbackUndefined(v, fallback) {
    return (v !== null && v !== undefined) ? v : fallback;
}

function vatUsesNBT(vat) {
    for (let i = 0; i < vat.length; i++) {
        const vatLayout = vat[i];
        if (vatLayout === undefined)
            continue;
        const fmt = vatLayout[10];//GX.Attr.NRM
        if (fmt === undefined)
            continue;
        const compCnt = fmt.compCnt;
        if (compCnt === 1 || compCnt === 2)//GX.CompCnt.NRM_NBT / GX.CompCnt.NRM_NBT3
            return true;
    }

    return false;
}

function compileVtxLoader(vatFormat, vcd) {
    const vat = [vatFormat];
    const desc = { vat, vcd };
    return compileVtxLoaderDesc(desc);
}

//const cache = new HashMap(vtxLoaderDescEqual, nullHashFunc);
function compileVtxLoaderDesc(desc) {
    let loader;
//    let loader = cache.get(desc);
//    if (loader === null) {
        const vat = desc.vat;
        const vcd = desc.vcd;
        // XXX(jstpierre): This is a bit sketchy, but what about NBT isn't sketchy...
        const useNBT = vatUsesNBT(vat);
        const loadedVertexLayout = compileLoadedVertexLayout(vcd, useNBT);
        loader = newVtxLoaderImpl(vat, vcd, loadedVertexLayout);
//        cache.add(loadedVertexLayout, loader);
//    }
    return loader;
}

function getSingleVatIndex(vat) {
    let singleVatIndex = -1;
    for (let i = 0; i < vat.length; i++) {
        const vatLayout = vat[i];
        if (vatLayout === undefined)
            continue;
        if (singleVatIndex >= 0)
            return null;
        singleVatIndex = i;
    }
    assert(singleVatIndex >= 0);
    return singleVatIndex;
}

function translateSourceVatLayout(vatFormat, vcd) {
    let srcVertexSize = 0;

    for (let vtxAttrib = 0; vtxAttrib < vcd.length; vtxAttrib++) {
        // Describes packed vertex layout.
        const vtxAttrDesc = vcd[vtxAttrib];
        // Describes format of pointed-to data.
        const vtxAttrFmt = vatFormat[vtxAttrib];

        if (!vtxAttrDesc || vtxAttrDesc.type === 0)//GX.AttrType.NONE
            continue;

        const srcIndexComponentCount = getIndexNumComponents(vtxAttrib, vtxAttrFmt);

        // MTXIDX entries can only be DIRECT if they exist.
        if (isVtxAttribMtxIdx(vtxAttrib))
            assert(vtxAttrDesc.type === 1);//GX.AttrType.DIRECT

        if (vtxAttrDesc.type === 1)//GX.AttrType.DIRECT
            srcVertexSize += getAttributeByteSizeRaw(vtxAttrib, vtxAttrFmt);
        else if (vtxAttrDesc.type === 2)//GX.AttrType.INDEX8
            srcVertexSize += 1 * srcIndexComponentCount;
        else if (vtxAttrDesc.type === 3)//GX.AttrType.INDEX16
            srcVertexSize += 2 * srcIndexComponentCount;
    }

    return { srcVertexSize, vatFormat, vcd };
}

function compileSingleVtxLoader(loadedVertexLayout, srcLayout) {
    const runVertices = generateRunVertices(loadedVertexLayout, srcLayout);
    const source = `
function run(dstVertexDataView, dstVertexDataOffs, dlView, drawCallIdx, vtxArrayViews, vtxArrayStrides) {
    ${runVertices}
    return drawCallIdx;
}
`;

    return compileFunction(source, `run`);
}

function newVtxLoaderImpl(vat, vcd, loadedVertexLayout) {
    //                   (vat: GX_VtxAttrFmt[][], vcd: GX_VtxDesc[], public loadedVertexLayout: LoadedVertexLayout)
    const o = Object.assign({}, VtxLoaderImpl);
    o.sourceLayouts = [];
    o.vtxLoaders = [];
    o.loadedVertexLayout = loadedVertexLayout;



    const singleVat = getSingleVatIndex(vat);
    if (singleVat !== null) {
        const sourceLayout = translateSourceVatLayout(vat[singleVat], vcd);
        o.sourceLayouts[singleVat] = sourceLayout;
        o.singleVatLoader = compileSingleVatLoader(loadedVertexLayout, sourceLayout);
    } else {
        // Initialize multi-VAT.
        for (let i = 0; i < vat.length; i++) {
            const vatLayout = vat[i];
            if (vatLayout === undefined)
                continue;

            const sourceLayout = translateSourceVatLayout(vat[i], vcd);
            o.sourceLayouts[i] = sourceLayout;
            o.vtxLoaders[i] = compileSingleVtxLoader(loadedVertexLayout, sourceLayout);
        }
    }

    o.vat = arrayCopy(vat, vatCopy);
    o.vcd = arrayCopy(vcd, vcdCopy);

    return o;
}

const VtxLoaderImpl = {//implements VtxLoader
    vat: undefined,
    vcd: undefined,
    sourceLayouts: undefined,
    vtxLoaders: undefined,
    loadedVertexLayout: undefined,
    // For Single VAT cases (optimization).
    singleVatLoader: null,
    parseDisplayList(srcBuffer, loadOptions) {
        function newDraw(indexOffset) {
            return {
                indexOffset,
                indexCount: 0,
                posMatrixTable: Array(10).fill(0xFFFF),
                texMatrixTable: Array(10).fill(0xFFFF),
            };
        }

        // Parse display list.
        const dlView = srcBuffer.createDataView();
        const drawCalls = [];
        const draws = [];
        let totalVertexCount = 0;
        let totalIndexCount = 0;
        let drawCallIdx = 0;
        let currentDraw = null;
        let currentXfmem = null;

        while (true) {
            if (drawCallIdx >= srcBuffer.byteLength)
                break;
            const cmd = dlView.getUint8(drawCallIdx);
            if (cmd === 0)
                break;

            // NOTE(jstpierre): This hardcodes some assumptions about the arrays and indexed units.
            switch (cmd) {
            case 0x20: { // Position Matrices / GX.Command.LOAD_INDX_A
                currentDraw = null;
                if (currentXfmem === null)
                    currentXfmem = newDraw(totalIndexCount);
                // PosMtx memory address space starts at 0x0000 and goes until 0x0400 (including TexMtx),
                // each element being 3*4 in size.
                const memoryElemSize = 3*4;
                const memoryBaseAddr = 0x0000;
                const table = currentXfmem.posMatrixTable;

                const arrayIndex = dlView.getUint16(drawCallIdx + 0x01);
                const addrLen = dlView.getUint16(drawCallIdx + 0x03);
                const len = (addrLen >>> 12) + 1;
                const addr = addrLen & 0x0FFF;
                const tableIndex = ((addr - memoryBaseAddr) / memoryElemSize) | 0;

                // For now -- it's technically valid but I'm not sure if BRRES uses it.
                if (len !== memoryElemSize)
                    throw Error();

                table[tableIndex] = arrayIndex;
                drawCallIdx += 0x05;

                continue;
            }
            case 0x30: { // Texture Matrices / GX.Command.LOAD_INDX_C
                currentDraw = null;
                if (currentXfmem === null)
                    currentXfmem = newDraw(totalIndexCount);
                // TexMtx memory address space is the same as PosMtx memory address space, but by convention
                // uses the upper 10 matrices. We enforce this convention.
                // Elements should be 3*4 in size. GD has ways to break this but BRRES should not generate this.
                const memoryElemSize = 3*4;
                const memoryBaseAddr = 0x0078;
                const table = currentXfmem.texMatrixTable;

                const arrayIndex = dlView.getUint16(drawCallIdx + 0x01);
                const addrLen = dlView.getUint16(drawCallIdx + 0x03);
                const len = (addrLen >>> 12) + 1;
                const addr = addrLen & 0x0FFF;
                const tableIndex = ((addr - memoryBaseAddr) / memoryElemSize) | 0;

                // For now -- it's technically valid but I'm not sure if BRRES uses it.
                if (len !== memoryElemSize)
                    throw Error();

                table[tableIndex] = arrayIndex;
                drawCallIdx += 0x05;

                continue;
            }
            case 0x28: // Normal Matrices / GX.Command.LOAD_INDX_B
            case 0x38: // Light Objects / GX.Command.LOAD_INDX_D
                // TODO(jstpierre): Load these arrays as well.
                drawCallIdx += 0x05;
                continue;
            }

            const primType = cmd & 0xF8;
            const vertexFormat = cmd & 0x07;

            const vertexCount = dlView.getUint16(drawCallIdx + 0x01);
            drawCallIdx += 0x03;
            const srcOffs = drawCallIdx;
            totalVertexCount += vertexCount;

            if (currentDraw === null) {
                if (currentXfmem !== null) {
                    currentDraw = currentXfmem;
                    currentXfmem = null;
                } else {
                    currentDraw = newDraw(totalIndexCount);
                }
                draws.push(currentDraw);
            }

            let indexCount = 0;
            switch (primType) {
            case 0x90://GX.Command.DRAW_TRIANGLES
                indexCount = vertexCount;
                break;
            case 0xA0://GX.Command.DRAW_TRIANGLE_FAN
            case 0x98://GX.Command.DRAW_TRIANGLE_STRIP
                indexCount = (vertexCount - 2) * 3;
                break;
            case 0x80://GX.Command.DRAW_QUADS
            case 0x88://GX.Command.DRAW_QUADS_2
                indexCount = ((vertexCount * 6) / 4) * 3;
                break;
            default:
                throw new Error(`Invalid data at ${hexzero(srcBuffer.byteOffset, 0x08)} / ${hexzero(drawCallIdx - 0x03, 0x04)} cmd ${hexzero(cmd, 0x02)}`);
            }

            drawCalls.push({ primType, vertexFormat, srcOffs, vertexCount });
            currentDraw.indexCount += indexCount;
            totalIndexCount += indexCount;

            const srcLayout = this.sourceLayouts[vertexFormat];

            // Skip over the index data.
            drawCallIdx += srcLayout.srcVertexSize * vertexCount;
        }

        // Construct the index buffer.
        const firstVertexId = (loadOptions !== undefined && loadOptions.firstVertexId !== undefined) ? loadOptions.firstVertexId : 0;

        let indexDataIdx = 0;
        const dstIndexData = new Uint16Array(totalIndexCount);
        let vertexId = firstVertexId;

        for (let z = 0; z < drawCalls.length; z++) {
            const drawCall = drawCalls[z];

            // Convert topology to triangles.
            switch (drawCall.primType) {
            case 0x90://GX.Command.DRAW_TRIANGLES
                // Copy vertices.
                for (let i = 0; i < drawCall.vertexCount; i++) {
                    dstIndexData[indexDataIdx++] = vertexId++;
                }
                break;
            case 0x98://GX.Command.DRAW_TRIANGLE_STRIP
                // First vertex defines original triangle.
                for (let i = 0; i < 3; i++) {
                    dstIndexData[indexDataIdx++] = vertexId++;
                }

                for (let i = 3; i < drawCall.vertexCount; i++) {
                    dstIndexData[indexDataIdx++] = vertexId - ((i & 1) ? 1 : 2);
                    dstIndexData[indexDataIdx++] = vertexId - ((i & 1) ? 2 : 1);
                    dstIndexData[indexDataIdx++] = vertexId++;
                }
                break;
            case 0xA0://GX.Command.DRAW_TRIANGLE_FAN
                // First vertex defines original triangle.
                const firstVertex = vertexId;

                for (let i = 0; i < 3; i++) {
                    dstIndexData[indexDataIdx++] = vertexId++;
                }

                for (let i = 3; i < drawCall.vertexCount; i++) {
                    dstIndexData[indexDataIdx++] = firstVertex;
                    dstIndexData[indexDataIdx++] = vertexId - 1;
                    dstIndexData[indexDataIdx++] = vertexId++;
                }
                break;
            case 0x80://GX.Command.DRAW_QUADS
            case 0x88://GX.Command.DRAW_QUADS_2
                // Each quad (4 vertices) is split into 2 triangles (6 vertices)
                for (let i = 0; i < drawCall.vertexCount; i += 4) {
                    dstIndexData[indexDataIdx++] = vertexId + 0;
                    dstIndexData[indexDataIdx++] = vertexId + 1;
                    dstIndexData[indexDataIdx++] = vertexId + 2;

                    dstIndexData[indexDataIdx++] = vertexId + 0;
                    dstIndexData[indexDataIdx++] = vertexId + 2;
                    dstIndexData[indexDataIdx++] = vertexId + 3;
                    vertexId += 4;
                }
            }
        }

        const dstVertexDataSize = this.loadedVertexLayout.vertexBufferStrides[0] * totalVertexCount;
        const dstVertexData = new ArrayBuffer(dstVertexDataSize);
        const vertexBuffers = [dstVertexData];

        const indexData = dstIndexData.buffer;
        return { indexData, totalIndexCount, totalVertexCount, draws: draws, vertexId, vertexBuffers, dlView, drawCalls };
    },
    loadVertexDataInto(dst, dstOffs, loadedVertexData, vtxArrays) {
        const vtxArrayViews = [];
        const vtxArrayStrides = [];
        for (let i = 0; i <= 20; i++) {//GX.Attr.MAX
            if (vtxArrays[i] !== undefined) {
                vtxArrayViews[i] = vtxArrays[i].buffer.createDataView(vtxArrays[i].offs);
                vtxArrayStrides[i] = vtxArrays[i].stride;
            }
        }

        const dlView = assertExists(loadedVertexData.dlView);
        const drawCalls = assertExists(loadedVertexData.drawCalls);

        const dstVertexDataSize = this.loadedVertexLayout.vertexBufferStrides[0] * loadedVertexData.totalVertexCount;
        assert(dst.byteLength >= dstVertexDataSize);
        let dstVertexDataOffs = dstOffs;

        // Now make the data.

        if (this.singleVatLoader !== null) {
            this.singleVatLoader(dst, dstVertexDataOffs, this.loadedVertexLayout, dlView, drawCalls, vtxArrayViews, vtxArrayStrides);
        } else {
            for (let i = 0; i < drawCalls.length; i++) {
                const drawCall = drawCalls[i];

                let drawCallIdx = drawCall.srcOffs;
                for (let j = 0; j < drawCall.vertexCount; j++) {
                    drawCallIdx = this.vtxLoaders[drawCall.vertexFormat](dst, dstVertexDataOffs, dlView, drawCallIdx, vtxArrayViews, vtxArrayStrides);
                    dstVertexDataOffs += this.loadedVertexLayout.vertexBufferStrides[0];
                }
            }
        }
    },
    loadVertexData(loadedVertexData, vtxArrays) {
        const dstVertexData = assertExists(loadedVertexData.vertexBuffers[0]);
        const dstVertexDataView = new DataView(dstVertexData);
        return this.loadVertexDataInto(dstVertexDataView, 0, loadedVertexData, vtxArrays);
    },
    runVertices(vtxArrays, srcBuffer, loadOptions) {
        const loadedVertexData = this.parseDisplayList(srcBuffer, loadOptions);
        this.loadVertexData(loadedVertexData, vtxArrays);
        return loadedVertexData;
    }
};

function compileSingleVatLoader(loadedVertexLayout, vatLayout) {
    const runVertices = generateRunVertices(loadedVertexLayout, vatLayout);
    const source = `
function runVertices(dstVertexDataView, dstVertexDataOffs, loadedVertexLayout, dlView, drawCalls, vtxArrayViews, vtxArrayStrides) {
    for (let i = 0; i < drawCalls.length; i++) {
        const drawCall = drawCalls[i];

        let drawCallIdx = drawCall.srcOffs;
        for (let j = 0; j < drawCall.vertexCount; j++) {
            ${runVertices}
            dstVertexDataOffs += loadedVertexLayout.vertexBufferStrides[0];
        }
    }
}
`;
    return compileFunction(source, `runVertices`);
}
function hexzero(n, spaces) {
    let S = n.toString(16);
    return leftPad(S, spaces);
}
function generateRunVertices(loadedVertexLayout, vatLayout) {
    function compileVtxArrayViewName(vtxAttrib) {
        return `vtxArrayViews[${vtxAttrib}]`;
    }

    // Loads a single vertex layout.
    function compileVatLayoutAttribute(vatLayout, vtxAttrib) {
        const vtxAttrFmt = vatLayout.vatFormat[vtxAttrib];
        const vtxAttrDesc = vatLayout.vcd[vtxAttrib];

        if (!vtxAttrDesc || vtxAttrDesc.type === 0)
            return '';

        const enableOutput = (vtxAttrDesc.enableOutput === undefined || vtxAttrDesc.enableOutput);

        const dstFormat = loadedVertexLayout.vertexAttributeFormats[vtxAttrib];
        const dstBaseOffs = loadedVertexLayout.vertexAttributeOffsets[vtxAttrib];

        let srcAttrByteSize = -1;

        // We only need vtxAttrFmt if we're going to read the data.
        if (vtxAttrDesc.type === 1)
            srcAttrByteSize = getAttributeByteSizeRaw(vtxAttrib, vtxAttrFmt);

        function compileShift(n) {
            // Instead of just doing `${n} >> srcAttrCompShift`, we use division
            // to get us the fractional components...
            const srcAttrCompShift = getComponentShift(vtxAttrib, vtxAttrFmt);
            const divisor = 1 << srcAttrCompShift;
            if (divisor === 1)
                return n;
            else
                return `(${n} / ${divisor})`;
        }

        function compileReadOneComponent(viewName, attrOffset) {
            switch (getComponentType(vtxAttrib, vtxAttrFmt)) {
            case 4:
                return `${viewName}.getFloat32(${attrOffset})`;
            case 0:
                return compileShift(`${viewName}.getUint8(${attrOffset})`);
            case 2:
                return compileShift(`${viewName}.getUint16(${attrOffset})`);
            case 1:
                return compileShift(`${viewName}.getInt8(${attrOffset})`);
            case 3:
                return compileShift(`${viewName}.getInt16(${attrOffset})`);
            default:
                throw "whoops";
            }
        }

        function compileWriteOneComponentF32(offs, value) {
            const littleEndian = (getSystemEndianness() === Endianness.LITTLE_ENDIAN);
            const dstOffs = `dstVertexDataOffs + ${offs}`;
            return `dstVertexDataView.setFloat32(${dstOffs}, ${value}, ${littleEndian})`;
        }

        function compileWriteOneComponentU8Norm(offs, value) {
            const dstOffs = `dstVertexDataOffs + ${offs}`;
            return `dstVertexDataView.setUint8(${dstOffs}, ${value} * 0xFF)`;
        }

        function compileWriteOneComponentU8(offs, value) {
            const dstOffs = `dstVertexDataOffs + ${offs}`;
            return `dstVertexDataView.setUint8(${dstOffs}, ${value})`;
        }

        function compileWriteOneComponent(offs, value) {
            const typeFlags = getFormatTypeFlags(dstFormat);
            const isNorm = getFormatFlags(dstFormat) & 0b00000001;
            if (typeFlags === 0x08)
                return compileWriteOneComponentF32(offs, value);
            else if (typeFlags === 0x01 && isNorm)
                return compileWriteOneComponentU8Norm(offs, value);
            else if (typeFlags === 0x01)
                return compileWriteOneComponentU8(offs, value);
            else
                throw "whoops";
        }

        function compileOneAttribColor(viewName, attrOffs) {
            const dstComponentCount = getFormatCompFlags(dstFormat);
            const dstOffs = dstBaseOffs;
            assert(dstComponentCount === 4);

            const temp = `_T${vtxAttrib}`;
            const componentType = getComponentType(vtxAttrib, vtxAttrFmt);
            if (componentType === 0) {
                return `
    var ${temp} = ${viewName}.getUint16(${attrOffs});
    ${compileWriteOneComponent(dstOffs + 0, `(((${temp} >>> 11) & 0x1F) / 0x1F)`)};
    ${compileWriteOneComponent(dstOffs + 1, `(((${temp} >>>  5) & 0x3F) / 0x3F)`)};
    ${compileWriteOneComponent(dstOffs + 2, `(((${temp} >>>  0) & 0x1F) / 0x1F)`)};
    ${compileWriteOneComponent(dstOffs + 3, `1.0`)};
`;
            } else if (componentType === 1 || componentType === 2) {
                return `
    ${compileWriteOneComponent(dstOffs + 0, `${viewName}.getUint8(${attrOffs} + 0) / 0xFF`)};
    ${compileWriteOneComponent(dstOffs + 1, `${viewName}.getUint8(${attrOffs} + 1) / 0xFF`)};
    ${compileWriteOneComponent(dstOffs + 2, `${viewName}.getUint8(${attrOffs} + 2) / 0xFF`)};
    ${compileWriteOneComponent(dstOffs + 3, `1.0`)};
`;
            } else if (componentType === 3) {
                return `
    var ${temp} = ${viewName}.getUint16(${attrOffs});
    ${compileWriteOneComponent(dstOffs + 0, `(((${temp} >>> 12) & 0x0F) / 0x0F)`)};
    ${compileWriteOneComponent(dstOffs + 1, `(((${temp} >>>  8) & 0x0F) / 0x0F)`)};
    ${compileWriteOneComponent(dstOffs + 2, `(((${temp} >>>  4) & 0x0F) / 0x0F)`)};
    ${compileWriteOneComponent(dstOffs + 3, `(((${temp} >>>  0) & 0x0F) / 0x0F)`)};
`;
            } else if (componentType === 4) {
                return `
    var ${temp} = (${viewName}.getUint8(${attrOffs} + 0) << 16) | (${viewName}.getUint8(${attrOffs} + 1) << 8) | (${viewName}.getUint8(${attrOffs} + 2));
    ${compileWriteOneComponent(dstOffs + 0, `(((${temp} >>> 18) & 0x3F) / 0x3F)`)};
    ${compileWriteOneComponent(dstOffs + 1, `(((${temp} >>> 12) & 0x3F) / 0x3F)`)};
    ${compileWriteOneComponent(dstOffs + 2, `(((${temp} >>>  6) & 0x3F) / 0x3F)`)};
    ${compileWriteOneComponent(dstOffs + 3, `(((${temp} >>>  0) & 0x3F) / 0x3F)`)};
`;
            } else if (componentType === 5) {
                return `
    ${compileWriteOneComponent(dstOffs + 0, `${viewName}.getUint8(${attrOffs} + 0) / 0xFF`)};
    ${compileWriteOneComponent(dstOffs + 1, `${viewName}.getUint8(${attrOffs} + 1) / 0xFF`)};
    ${compileWriteOneComponent(dstOffs + 2, `${viewName}.getUint8(${attrOffs} + 2) / 0xFF`)};
    ${compileWriteOneComponent(dstOffs + 3, `${viewName}.getUint8(${attrOffs} + 3) / 0xFF`)};
`;
            } else {
                throw "whoops";
            }
        }

        function compileOneAttribMtxIdx(viewName, attrOffs) {
            let S = ``;

            const srcAttrCompSize = getAttributeComponentByteSize(vtxAttrib, vtxAttrFmt);
            const srcAttrCompCount = getAttributeComponentCount(vtxAttrib, vtxAttrFmt);
            assertExists(srcAttrCompSize === 1 && srcAttrCompCount === 1);

            const dstOffs = dstBaseOffs;
            const srcOffs = `${attrOffs}`;
            const value = compileReadOneComponent(viewName, srcOffs);

            S += `
    ${compileWriteOneComponent(dstOffs, `(${value} / 3)`)};`;

            return S;
        }

        function compileOneAttribOther(viewName, attrOffs) {
            let S = ``;

            const srcAttrCompSize = getAttributeComponentByteSize(vtxAttrib, vtxAttrFmt);
            const srcAttrCompCount = getAttributeComponentCount(vtxAttrib, vtxAttrFmt);

            const dstComponentSize = getFormatCompByteSize(dstFormat);

            for (let i = 0; i < srcAttrCompCount; i++) {
                const dstOffs = dstBaseOffs + (i * dstComponentSize);
                const srcOffs = `${attrOffs} + ${i * srcAttrCompSize}`;
                const value = compileReadOneComponent(viewName, srcOffs);

                S += `
    ${compileWriteOneComponent(dstOffs, value)};`;
            }

            return S;
        }

        function compileOneAttrib(viewName, attrOffsetBase, drawCallIdxIncr) {
            let S = ``;

            if (enableOutput) {
                if (isVtxAttribMtxIdx(vtxAttrib))
                    S += compileOneAttribMtxIdx(viewName, attrOffsetBase);
                else if (isVtxAttribColor(vtxAttrib))
                    S += compileOneAttribColor(viewName, attrOffsetBase);
                else
                    S += compileOneAttribOther(viewName, attrOffsetBase);
            }

            S += `
    drawCallIdx += ${drawCallIdxIncr};
`;

            return S;
        }

        function compileOneIndex(viewName, readIndex, drawCallIdxIncr, uniqueSuffix = '') {
            const stride = `vtxArrayStrides[${vtxAttrib}]`;
            const attrOffsetBase = `(${readIndex}) * ${stride}`;
            const arrayOffsetVarName = `arrayOffset${vtxAttrib}${uniqueSuffix}`;

            if (enableOutput) {
                return `const ${arrayOffsetVarName} = ${attrOffsetBase};${compileOneAttrib(viewName, arrayOffsetVarName, drawCallIdxIncr)}`;
            } else {
                return compileOneAttrib('', '', drawCallIdxIncr);
            }
        }

        function compileAttribIndex(viewName, readIndex, drawCallIdxIncr) {
            if (vtxAttrib === 10 && vtxAttrFmt.compCnt === 2) {
                // Special case: NBT3.
                return `
    // NRM
    ${compileOneIndex(viewName, readIndex, drawCallIdxIncr, `_N`)}
    // BINRM
    ${compileOneIndex(viewName, readIndex, drawCallIdxIncr, `_B`)}
    // TANGENT
    ${compileOneIndex(viewName, readIndex, drawCallIdxIncr, `_T`)}`;
            } else {
                return `
    // ${getAttrName(vtxAttrib)}
    ${compileOneIndex(viewName, readIndex, drawCallIdxIncr)}`;
            }
        }

        switch (vtxAttrDesc.type) {
        case 1:
            return compileOneAttrib(`dlView`, `drawCallIdx`, srcAttrByteSize);
        case 2:
            return compileAttribIndex(compileVtxArrayViewName(vtxAttrib), `dlView.getUint8(drawCallIdx)`, 1);
        case 3:
            return compileAttribIndex(compileVtxArrayViewName(vtxAttrib), `dlView.getUint16(drawCallIdx)`, 2);
        default:
            throw "whoops";
        }
    }

    function compileVatLayout(vatLayout) {
        let S = '';
        for (let vtxAttrib = 0; vtxAttrib <= 20; vtxAttrib++)
            S += compileVatLayoutAttribute(vatLayout, vtxAttrib);
        return S;
    }

    return compileVatLayout(vatLayout);
}

function getAttrName(vtxAttrib) {
    switch (vtxAttrib) {
    case 0:   return `PNMTXIDX`;
    case 1: return `TEX0MTXIDX`;
    case 2: return `TEX1MTXIDX`;
    case 3: return `TEX2MTXIDX`;
    case 4: return `TEX3MTXIDX`;
    case 5: return `TEX4MTXIDX`;
    case 6: return `TEX5MTXIDX`;
    case 7: return `TEX6MTXIDX`;
    case 8: return `TEX7MTXIDX`;
    case 9:        return `POS`;
    case 10:        return `NRM`;
    case 11:       return `CLR0`;
    case 12:       return `CLR1`;
    case 13:       return `TEX0`;
    case 14:       return `TEX1`;
    case 15:       return `TEX2`;
    case 16:       return `TEX3`;
    case 17:       return `TEX4`;
    case 18:       return `TEX5`;
    case 19:       return `TEX6`;
    case 20:       return `TEX7`;
    default:
        throw new Error("whoops");
    }
}

function getComponentType(vtxAttrib, vatFormat) {
    if (isVtxAttribMtxIdx(vtxAttrib))
        return 0;

    return vatFormat.compType;
}

function getComponentShiftRaw(compType, compShift) {
    switch (compType) {
    case 4:
    case 5:
        return 0;
    case 0:
    case 1:
    case 2:
    case 3:
        return compShift;
    }
}

function getComponentShift(vtxAttrib, vatFormat) {
    // MTXIDX fields don't have VAT entries.
    if (isVtxAttribMtxIdx(vtxAttrib))
        return 0;

    // Normals *always* use either 6 or 14 for their shift values.
    // The value in the VAT is ignored. Note that normals are also normalized, too.
    if (vtxAttrib === 10) {
        if (vatFormat.compType === 0 || vatFormat.compType === 1)
            return 6;
        else if (vatFormat.compType === 2 || vatFormat.compType === 3)
            return 14;
        else
            throw "whoops";
    }

    return getComponentShiftRaw(vatFormat.compType, vatFormat.compShift);
}

function getFormatCompFlags(fmt) {
    return (fmt >>>  8) & 0xFF;
}

function compileFunction(source, entryPoint) {
    const fullSource = `
"use strict";

${source}

return function() {
    return ${entryPoint};
}();
`;

    const generator = new Function(fullSource);
    const func = generator();
    return func;
}

function compileLoadedVertexLayout(vcd, useNBT = false) {
    //                            (vcd: GX_VtxDesc[], useNBT: boolean = false): LoadedVertexLayout {
    const bufferIndex = 0;

    function getFormatForAttrInput(attrInput) {
        switch (attrInput) {
        case VertexAttributeInput.TEX0123MTXIDX:
        case VertexAttributeInput.TEX4567MTXIDX:
            return GfxFormatU8_RGBA_NORM;
        case VertexAttributeInput.POS:
            return GfxFormatF32_RGBA; // Also can include PNMTXIDX if the material requests it; assume it does.
        case VertexAttributeInput.NRM:
        case VertexAttributeInput.TANGENT:
        case VertexAttributeInput.BINRM:
            return GfxFormatF32_RGB;
        case VertexAttributeInput.CLR0:
        case VertexAttributeInput.CLR1:
            return GfxFormatU8_RGBA_NORM;
        case VertexAttributeInput.TEX01:
        case VertexAttributeInput.TEX23:
        case VertexAttributeInput.TEX45:
        case VertexAttributeInput.TEX67:
            return GfxFormatF32_RGBA;
        default:
            throw "whoops";
        }
    }

    function allocateVertexInput(attrInput, format = getFormatForAttrInput(attrInput)) {
        const existingInput = singleVertexInputLayouts.find((layout) => layout.attrInput === attrInput);

        if (existingInput !== undefined) {
            return existingInput;
        } else {
            const formatComponentSize = getFormatCompByteSize(format);
            const formatComponentCount = getFormatCompFlags(format);//getFormatComponentCount / getFormatCompFlagsComponentCount

            dstVertexSize = align(dstVertexSize, formatComponentSize);
            const bufferOffset = dstVertexSize;
            dstVertexSize += formatComponentSize * formatComponentCount;
            const input = { attrInput, bufferIndex, bufferOffset, format };
            singleVertexInputLayouts.push(input);
            return input;
        }
    }

    // Create destination vertex layout.
    let dstVertexSize = 0;
    const singleVertexInputLayouts = [];//: SingleVertexInputLayout[]
    const vertexAttributeOffsets = [];
    const vertexAttributeFormats = [];//: GfxFormat[]
    for (let vtxAttrib = 0; vtxAttrib < vcd.length; vtxAttrib++) {
        const vtxAttrDesc = vcd[vtxAttrib];
        if (!vtxAttrDesc || vtxAttrDesc.type === 0)//GX.AttrType.NONE
            continue;

        const outputMode = fallbackUndefined(vtxAttrDesc.outputMode, 0);//GX_VtxDescOutputMode.VertexData
        if (outputMode === 2)//GX_VtxDescOutputMode.None
            continue;

        let input;//: SingleVertexInputLayout
        let fieldFormat;
        let fieldCompOffset = 0;

        if (outputMode === 1) {//GX_VtxDescOutputMode.Index
            const attrInput = getAttrInputForAttr(vtxAttrib);
            input = allocateVertexInput(attrInput, GfxFormatU16_R);
            fieldFormat = input.format;
        } else if (isVtxAttribTexMtxIdx(vtxAttrib)) {
            // Allocate the base if it doesn't already exist.
            const attrInput = (vtxAttrib < 5) ? VertexAttributeInput.TEX0123MTXIDX : VertexAttributeInput.TEX4567MTXIDX;//GX.Attr.TEX4MTXIDX
            input = allocateVertexInput(attrInput);
            fieldCompOffset = (vtxAttrib - 1) & 0x03;//GX.Attr.TEX0MTXIDX
            fieldFormat = GfxFormatU8_RGBA;
        } else if (vtxAttrib === 9) {//GX.Attr.POS
            // POS and PNMTX are packed together.
            input = allocateVertexInput(VertexAttributeInput.POS);
            fieldFormat = GfxFormatF32_RGB;
        } else if (vtxAttrib === 0) {//GX.Attr.PNMTXIDX
            // PNMTXIDX is packed in w of POS.
            input = allocateVertexInput(VertexAttributeInput.POS);
            fieldCompOffset = 3;
            fieldFormat = GfxFormatF32_R;
        } else if (vtxAttrib === 10 && useNBT) {//GX.Attr.NRM
            // NBT. Allocate inputs for all of NRM, BINRM, TANGENT.
            input = allocateVertexInput(VertexAttributeInput.NRM);
            allocateVertexInput(VertexAttributeInput.BINRM);
            allocateVertexInput(VertexAttributeInput.TANGENT);
            fieldFormat = input.format;
        } else if (vtxAttrib === 10) {//GX.Attr.NRM
            // Regular NRM.
            input = allocateVertexInput(VertexAttributeInput.NRM);
            fieldFormat = input.format;
        } else if (isVtxAttribTex(vtxAttrib)) {
            const texAttr = vtxAttrib - 13;//GX.Attr.TEX0
            const attrInput = VertexAttributeInput.TEX01 + (texAttr >>> 1);
            input = allocateVertexInput(attrInput);
            fieldCompOffset = (texAttr & 0x01) * 2;
            fieldFormat = GfxFormatF32_RG;
        } else if (isVtxAttribColor(vtxAttrib)) {
            const attrInput = getAttrInputForAttr(vtxAttrib);
            input = allocateVertexInput(attrInput);
            fieldFormat = input.format;
        } else {
            throw "whoops";
        }

        const fieldByteOffset = getFormatCompByteSize(input.format) * fieldCompOffset;
        vertexAttributeOffsets[vtxAttrib] = input.bufferOffset + fieldByteOffset;
        vertexAttributeFormats[vtxAttrib] = fieldFormat;
    }

    // Align the whole thing to our minimum required alignment (F32).
    dstVertexSize = align(dstVertexSize, 4);
    const vertexBufferStrides = [dstVertexSize];

    const indexFormat = GfxFormatU16_R;

    return { indexFormat, vertexBufferStrides, singleVertexInputLayouts, vertexAttributeOffsets, vertexAttributeFormats };
}

function vatCopy(a) {
    if (a === undefined)
        return [];
    else
        return arrayCopy(a, vtxAttrFmtCopy);
}

function vtxAttrFmtCopy(a) {
    if (a === undefined)
        return undefined;
    else
        return { compCnt: a.compCnt, compShift: a.compShift, compType: a.compType };
}

function vcdCopy(a) {
    if (a === undefined)
        return undefined;
    else
        return { enableOutput: a.enableOutput, type: a.type };
}

function translateVatLayout(vatFormat, vcd) {
    if (vatFormat === undefined)
        return undefined;

    let srcVertexSize = 0;

    for (let vtxAttrib = 0; vtxAttrib < vcd.length; vtxAttrib++) {
        // Describes packed vertex layout.
        const vtxAttrDesc = vcd[vtxAttrib];
        // Describes format of pointed-to data.
        const vtxAttrFmt = vatFormat[vtxAttrib];

        if (!vtxAttrDesc || vtxAttrDesc.type === 0)
            continue;

        const srcIndexComponentCount = getIndexNumComponents(vtxAttrib, vtxAttrFmt);

        // MTXIDX entries can only be DIRECT if they exist.
        if (isVtxAttribMtxIdx(vtxAttrib))
            assert(vtxAttrDesc.type === 1);

        if (vtxAttrDesc.type === 1)
            srcVertexSize += getAttributeByteSizeRaw(vtxAttrib, vtxAttrFmt);
        else if (vtxAttrDesc.type === 2)
            srcVertexSize += 1 * srcIndexComponentCount;
        else if (vtxAttrDesc.type === 3)
            srcVertexSize += 2 * srcIndexComponentCount;
    }

    return { srcVertexSize, vatFormat, vcd };
}

function getIndexNumComponents(vtxAttrib, vatFormat) {
    if (vtxAttrib === 10 && vatFormat.compCnt === 2)
        return 3;
    else
        return 1;
}

function arrayCopy(a, copyFunc) {
    const b = Array(a.length);
    for (let i = 0; i < a.length; i++)
        b[i] = copyFunc(a[i]);
    return b;
}

function isVtxAttribMtxIdx(vtxAttrib) {
    return vtxAttrib === 0 || isVtxAttribTexMtxIdx(vtxAttrib);//GX.Attr.PNMTXIDX
}

function getAttributeByteSize(vat, vtxAttrib) {
    return getAttributeByteSizeRaw(vtxAttrib, vat[vtxAttrib]);
}

function getAttributeByteSizeRaw(vtxAttrib, vatFormat) {
    // MTXIDX fields don't have VAT entries.
    if (isVtxAttribMtxIdx(vtxAttrib))
        return 1;

    // Color works differently.
    if (isVtxAttribColor(vtxAttrib)) {
        switch (parseInt(vatFormat.compType)) {
        case 0://GX.CompType.RGB565
            return 2;
        case 1://GX.CompType.RGB8
            return 3;
        case 2://GX.CompType.RGBX8
            return 4;
        case 3://GX.CompType.RGBA4
            return 2;
        case 4://GX.CompType.RGBA6
            return 3;
        case 5://GX.CompType.RGBA8
            return 4;
        }
    }

    const compSize = getAttributeComponentByteSize(vtxAttrib, vatFormat);
    const compCount = getAttributeComponentCount(vtxAttrib, vatFormat);
    return compSize * compCount;
}

function getAttributeComponentByteSize(vtxAttrib, vatFormat) {
    // MTXIDX fields don't have VAT entries.
    if (isVtxAttribMtxIdx(vtxAttrib))
        return 1;

    return getAttributeComponentByteSizeRaw(vatFormat.compType);
}

function getAttributeComponentByteSizeRaw(compType) {
    switch (parseInt(compType)) {
    case 0://GX.CompType.U8
    case 1://GX.CompType.S8
    case 5://GX.CompType.RGBA8
        return 1;
    case 2://GX.CompType.U16
    case 3://GX.CompType.S16
        return 2;
    case 4://GX.CompType.F32
        return 4;
    }
}

function isVtxAttribTexMtxIdx(vtxAttrib) {
    switch (parseInt(vtxAttrib)) {
    case 1://GX.Attr.TEX0MTXIDX
    case 2://GX.Attr.TEX1MTXIDX
    case 3://GX.Attr.TEX2MTXIDX
    case 4://GX.Attr.TEX3MTXIDX
    case 5://GX.Attr.TEX4MTXIDX
    case 6://GX.Attr.TEX5MTXIDX
    case 7://GX.Attr.TEX6MTXIDX
    case 8://GX.Attr.TEX7MTXIDX
        return true;
    default:
        return false;
    }
}

function isVtxAttribColor(vtxAttrib) {
    switch (parseInt(vtxAttrib)) {
    case 11://GX.Attr.CLR0
    case 12://GX.Attr.CLR1
        return true;
    default:
        return false;
    }
}

function isVtxAttribTex(vtxAttrib) {
    switch (vtxAttrib) {
    case 13://GX.Attr.TEX0
    case 14:
    case 15:
    case 16:
    case 17:
    case 18:
    case 19:
    case 20://GX.Attr.TEX7
        return true;
    default:
        return false;
    }
}

function getAttrInputForAttr(attrib) {
    if (attrib === 9)
        return 2;
    else if (attrib === 10)
        return 3;
    else if (attrib === 11)
        return 6;
    else if (attrib === 12)
        return 7;
    else
        throw "whoops";
}

function getAttributeComponentCount(vtxAttrib, vatFormat) {
    //getFormatCompFlagsComponentCount
    return getAttributeFormatCompFlags(vtxAttrib, vatFormat);
}

function getAttributeFormatCompFlags(vtxAttrib, vatFormat) {
    // MTXIDX fields don't have VAT entries.
    if (isVtxAttribMtxIdx(vtxAttrib))
        return 0x01;//FormatCompFlags.COMP_R

    return getAttributeFormatCompFlagsRaw(vtxAttrib, vatFormat.compCnt);
}

function getAttributeFormatCompFlagsRaw(vtxAttrib, compCnt) {
    switch (parseInt(vtxAttrib)) {
    case 9://GX.Attr.POS
        if (compCnt === 0)//GX.CompCnt.POS_XY
            return 0x02;//FormatCompFlags.COMP_RG
        else if (compCnt === 1)//GX.CompCnt.POS_XYZ
            return 0x03;//FormatCompFlags.COMP_RGB
    case 10://GX.Attr.NRM
        // Normals always have 3 components per index.
        return 0x03;//FormatCompFlags.COMP_RGB
    case 11://GX.Attr.CLR0
    case 12://GX.Attr.CLR1
        if (compCnt === 0)//GX.CompCnt.CLR_RGB
            return 0x03;//FormatCompFlags.COMP_RGB
        else if (compCnt === 1)//GX.CompCnt.CLR_RGBA
            return 0x04;//FormatCompFlags.COMP_RGBA
    case 13://GX.Attr.TEX0
    case 14://GX.Attr.TEX1
    case 15://GX.Attr.TEX2
    case 16://GX.Attr.TEX3
    case 17://GX.Attr.TEX4
    case 18://GX.Attr.TEX5
    case 19://GX.Attr.TEX6
    case 20://GX.Attr.TEX7
        if (compCnt === 0)//GX.CompCnt.TEX_S
            return 0x01;//FormatCompFlags.COMP_R
        else if (compCnt === 1)//GX.CompCnt.TEX_ST
            return 0x02;//FormatCompFlags.COMP_RG
    case 0xFF://GX.Attr.NULL
    default:
        // Shouldn't ever happen
        throw "whoops";
    }
}

function getAttributeBaseFormat(vtxAttrib) {
    const GfxFormatU8_R_NORM = makeFormat(0x01, 0x01, 0b00000001);
    // MTXIDX are packed special. See code below in compileLoadedVertexLayout.
    if (isVtxAttribMtxIdx(vtxAttrib))
        return GfxFormatU8_R_NORM;

    // To save on space, we put color data in U8.
    if (vtxAttrib === 11 || vtxAttrib === 12)
        return GfxFormatU8_R_NORM;

    // In theory, we could use U8_R/S8_R/S16_R/U16_R for the other types,
    // but we can't easily express compShift, so we fall back to F32 for now.
    return makeFormat(0x08, 0x01, 0b00000000);
}

function getAttributeFormat(vatLayouts, vtxAttrib) {
    let formatCompFlags = 0;

    const baseFormat = getAttributeBaseFormat(vtxAttrib);

    if (vtxAttrib === 9) {
        // We pack PNMTXIDX into w of POS.
        formatCompFlags = 0x04;
    } else if (isVtxAttribColor(vtxAttrib)) {
        // For color attributes, we always output all 4 components.
        formatCompFlags = 0x04;
    } else if (isVtxAttribTexMtxIdx(vtxAttrib)) {
        // We pack TexMtxIdx into multi-channel vertex inputs.
        formatCompFlags = 0x04;
    } else if (isVtxAttribTex(vtxAttrib)) {
        assert(baseFormat === (0x08 << 16) | (0x01 << 8));
        formatCompFlags = 0x04;
    } else {
        // Go over all layouts and pick the best one.
        for (let i = 0; i < vatLayouts.length; i++) {
            const vatLayout = vatLayouts[i];
            if (vatLayout !== undefined)
                formatCompFlags = Math.max(formatCompFlags, getAttributeFormatCompFlags(vtxAttrib, vatLayout.vatFormat[vtxAttrib]));
        }
    }

    return makeFormat(getFormatTypeFlags(baseFormat), formatCompFlags, getFormatFlags(baseFormat));
}

function makeFormat(type, comp, flags) {
    return (type << 16) | (comp << 8) | flags;
}

function getFormatTypeFlags(fmt) {
    return (fmt >>> 16) & 0xFF;
}

function getFormatFlags(fmt) {
    return fmt & 0xFF;
}

function getFormatCompByteSize(fmt) {
    return getFormatTypeFlagsByteSize((fmt >>> 16) & 0xFF);
}

function getFormatTypeFlagsByteSize(typeFlags) {
    switch (typeFlags) {
    case 0x08:
    case 0x03:
    case 0x06:
        return 4;
    case 0x02:
    case 0x05:
    case 0x07:
        return 2;
    case 0x01:
    case 0x04:
        return 1;
    default:
        throw "whoops";
    }
}

function align(n, multiple) {
    const mask = (multiple - 1);
    return (n + mask) & ~mask;
}

function nArray(n, c) {
    const d = new Array(n);
    for (let i = 0; i < n; i++)
        d[i] = c(i);
    return d;
}

function isVatLayoutNBT(vatLayout) {
    const compCnt = vatLayout.vatFormat[10].compCnt;
    return compCnt === 1 || compCnt === 2;
}

//arrayEqual<T>(a: T[], b: T[], e: EqualFunc<T>): boolean
function arrayEqual(a, b, e) {
    if (a.length !== b.length)
        return false;
    for (let i = 0; i < a.length; i++)
        if (!e(a[i], b[i]))
            return false;
    return true;
}

//a: LoadedVertexDraw, b: LoadedVertexDraw): boolean
function canMergeDraws(a, b) {
    if (a.indexOffset !== b.indexOffset)
        return false;
    if (!arrayEqual(a.posMatrixTable, b.posMatrixTable, (i, j) => i === j))
        return false;
    if (!arrayEqual(a.texMatrixTable, b.texMatrixTable, (i, j) => i === j))
        return false;
    return true;
}

//loadedDatas: LoadedVertexData[]): LoadedVertexData
function coalesceLoadedDatas(loadedDatas) {
    let totalIndexCount = 0;
    let totalVertexCount = 0;
    let indexDataSize = 0;
    let packedVertexDataSize = 0;
    const draws = [];//LoadedVertexDraw[]

    for (let i = 0; i < loadedDatas.length; i++) {
        const loadedData = loadedDatas[i];
        assert(loadedData.vertexBuffers.length === 1);

        for (let j = 0; j < loadedData.draws.length; j++) {
            const draw = loadedData.draws[j];
            const existingDraw = draws.length > 0 ? draws[draws.length - 1] : null;

            if (existingDraw !== null && canMergeDraws(draw, existingDraw)) {
                existingDraw.indexCount += draw.indexCount;
            } else {
                const indexOffset = totalIndexCount + draw.indexOffset;
                const indexCount = draw.indexCount;
                const posNrmMatrixTable = draw.posMatrixTable;
                const texMatrixTable = draw.texMatrixTable;
                draws.push({ indexOffset, indexCount, posMatrixTable: posNrmMatrixTable, texMatrixTable });
            }
        }

        totalIndexCount += loadedData.totalIndexCount;
        totalVertexCount += loadedData.totalVertexCount;
        indexDataSize += loadedData.indexData.byteLength;
        packedVertexDataSize += loadedData.vertexBuffers[0].byteLength;
    }

    const indexData = new Uint8Array(indexDataSize);
    const packedVertexData = new Uint8Array(packedVertexDataSize);

    let indexDataOffs = 0;
    let packedVertexDataOffs = 0;
    for (let i = 0; i < loadedDatas.length; i++) {
        const loadedData = loadedDatas[i];
        indexData.set(new Uint8Array(loadedData.indexData), indexDataOffs);
        packedVertexData.set(new Uint8Array(loadedData.vertexBuffers[0]), packedVertexDataOffs);
        indexDataOffs += loadedData.indexData.byteLength;
        packedVertexDataOffs += loadedData.vertexBuffers[0].byteLength;
    }

    return {
        indexData: indexData.buffer,
        vertexBuffers: [packedVertexData.buffer],
        totalIndexCount,
        totalVertexCount,
        vertexId: 0,
        draws,
        drawCalls: null,
        dlView: null,
    };
}

module.exports = {
    compileVtxLoader,
    coalesceLoadedDatas,
    makeFormat
};