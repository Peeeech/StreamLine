import os
import sys
import re
import json
import bpy #type: ignore
from dataclasses import asdict
    
def parseSamplers(samplers):
    return [s for s in samplers if s is not None]
    
def build_materials_from_scene(data, images, context=None):
    materials = data.values
    mats = []

    if context:
        prefix = context.scene.mat_prefix

    #Phase 1. Make DMDMaterial containers in their own collection so that everything can be preserved, and then blender-variants can interpret from these
    for i, data in enumerate(materials):
        matEmpty = bpy.data.objects.new(f"{prefix}{data.name}", None)
        idProp = matEmpty.ttyd_world_empty
        idProp.isMaterial = True

        props = matEmpty.ttyd_world_material
        props.name = data.name
        props.color = (data.color.r, data.color.g, data.color.b, data.color.a)

        if data.matSrc == 0:
            props.matSrc = 'matCol'
        elif data.matSrc == 1:
            props.matSrc = 'vtxCol'
        else:
            print(f"Material Color Source not found on {data.name}. {data.matSrc}")

        props.unk_009 = data.unk_009 #subtract vtex alpha flag?. seems always True for "_v" and "_v_x" mats

        #this blendMode relates to source colors inside nodes, actual 'full-mat-transparency' is dictated per-sampler on unk_0a
        if data.blendMode == 0:
            props.blendMode = 'opaque'
        elif data.blendMode == 1: 
            props.blendMode = 'clip'
        elif data.blendMode == 2:
            props.blendMode = 'full'
        else:
            print(f"Material Blend Mode not found on {data.name}. {data.matSrc}")

        validSamplers = parseSamplers(data.textureSamplers)
        props.numTextures = len(validSamplers)
        props.blendAlphaModulationR = (data.blendAlphaModulationR.r, data.blendAlphaModulationR.g, data.blendAlphaModulationR.b, data.blendAlphaModulationR.a)
        for i in range(props.numTextures):
            smp = props.textureSamplers.add()
            smp.wrapS = validSamplers[i].wrapS
            smp.wrapT = validSamplers[i].wrapT
            smp.unk_0a = validSamplers[i].unk_0a
            smp.unk_0b = validSamplers[i].unk_0b
            
            smp.texture.image = bpy.data.images.get(f"{prefix}{validSamplers[i].texture.name}")
            imageEmpty = bpy.data.objects.get(f"{prefix}{validSamplers[i].texture.name}")
            imageEmpty.ttyd_world_texture.render_order = validSamplers[i].texture.render_order

            smp.texture.name = validSamplers[i].texture.name
            smp.texture.render_order = validSamplers[i].texture.render_order
            smp.texture.wWidth = validSamplers[i].texture.wWidth
            smp.texture.wHeight = validSamplers[i].texture.wHeight

            txCrd = smp.texCoord
            txCrd.translateX = data.textureCoordTransforms[i].translateX
            txCrd.translateY = data.textureCoordTransforms[i].translateY
            txCrd.scaleX = data.textureCoordTransforms[i].scaleX
            txCrd.scaleY = data.textureCoordTransforms[i].scaleY
            txCrd.rotateZ = data.textureCoordTransforms[i].rotateZ
            txCrd.warpX = data.textureCoordTransforms[i].warpX
            txCrd.warpY = data.textureCoordTransforms[i].warpY
        props.tevConfig.tevMode = data.tevConfig.tevMode
        
        #Phase 2. Create base blender preview material and append the main one to the empty (extras can be appended on their creation)
        material = bpy.data.materials.new(f"[DrawMode 0] {prefix}{data.name}")
        material.show_transparent_back = False

        ref = props.materialRefs.add()
        ref.material = material
        
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        nodes.clear()

        output_node = nodes.new("ShaderNodeOutputMaterial")
        output_node.name = ("Output")
        output_shader_input = output_node.inputs['Surface']

        #First we're gonna create a node for either VertexColors or an RGB (Material Color) depending on MatSrc
        if props.matSrc == 'matCol':
            color0_node = nodes.new("ShaderNodeRGB")
            color0_node.outputs['Color'].default_value = props.color
            color0_node_alpha = None

        elif props.matSrc == 'vtxCol':
            color0_node = nodes.new("ShaderNodeVertexColor")
            color0_node.layer_name = "Col"
            color0_node_alpha = color0_node.outputs['Alpha']

        else:
            print(f"{props.name} failed matSrc check?")

        transparent_node = nodes.new("ShaderNodeBsdfTransparent")
        transparent_node.name = ("Transparent")
        transparent_output = transparent_node.outputs['BSDF']

        #NOTE: The blendMode here is used *purely* for Vertex Alpha, so we can set up nodes, but 'blend_method' will only be changed by meshDesc->drawMode

        color0_node.name = "Color0"
        color0_node_color = color0_node.outputs['Color']

        #Next we're gonna check for the presence of a sampler(s), and create ImageTex nodes depending on which sampler is pulled.
        # we're gonna pre-emptively make a transparent node per-texCoord and hook it's alpha into it for easy linking purposes

        tex_nodes = []

        for i, sampler in enumerate(validSamplers):
            tex = nodes.new("ShaderNodeTexImage")
            tex.image = bpy.data.images.get(f"{prefix}{validSamplers[i].texture.name}")
            tex.label = f"TEX{i}"
            tex.name = f"TEX{i}"
            tex_nodes.append(tex)

        diffuse_node = nodes.new("ShaderNodeBsdfDiffuse")
        diffuse_node.name = ("Diffuse")
        diffuse_input = diffuse_node.inputs['Color']
        diffuse_output = diffuse_node.outputs['BSDF']

        
            # Alpha check should be viable at the end, as long as the final color input routes into the Diffuse
            # BSDF, we can just check for it's input link and for the transparent node data

        #NOTE: It seems that [mat] with no suffix is MaterialRGB (matSrc = 0)
            # [mat]_v seems to be vertex colors
            # [mat]_x is presumably vertex alpha


        # CASE1: No samplers (matSrc 0 / 1)
        if len(validSamplers) == 0:
            color0_node.location = (-250, 0)
            output_node.location = (250, 0)

            links.new(color0_node_color, diffuse_input)
            links.new(diffuse_output, output_shader_input)
            finalShader = diffuse_output

        # CASE2: One sampler (matSrc 0 / 1)
        if len(validSamplers) >= 1:

            #couple different things seem to need to trigger 'blend' to display properly
            if props.blendMode == 'full':
                material.blend_method = 'BLEND'

            #this var seems to track if tex alpha should be subtracted?
            for i, smp in enumerate(validSamplers):
                if validSamplers[i].unk_0a == 1:
                    material.blend_method = 'BLEND' #might supposed to be clip, but some cases display weird artifacts when not on blend
                elif validSamplers[i].unk_0a == 2:
                    material.blend_method = 'BLEND'

            texNode0 = nodes.get("TEX0")
            rgbMath_node0 = nodes.new("ShaderNodeVectorMath")
            rgbMath_node0.name = ("Color0 Mix")
            shaderMix_node = nodes.new("ShaderNodeMixShader")
            shaderMix_node.name = ("Shader Mix")
            uvmap_node = nodes.new("ShaderNodeUVMap")
            mapping_node = nodes.new("ShaderNodeMapping")
            uvmap_node.uv_map = "UVMap"
            rgbMath_node0.operation = 'MULTIPLY'
            finalShader = shaderMix_node.outputs['Shader']

            uvmap_node.location = (-1150, 0)
            mapping_node.location = (-950, -200)
            output_node.location = (300, 0)
            texNode0.location = (-500, 0)
            color0_node.location = (-450, -300)
            diffuse_node.location = (-50, 0)
            rgbMath_node0.location = (-225, -200)
            transparent_node.location = (-50, 100)
            shaderMix_node.location = (125, 50)

            links.new(color0_node_color, rgbMath_node0.inputs[1])
            links.new(rgbMath_node0.outputs['Vector'], diffuse_input)            
            links.new(transparent_output, shaderMix_node.inputs[1])
            links.new(diffuse_output, shaderMix_node.inputs[2])

            samplerWrapPreview(texNode0, validSamplers[0].wrapS, validSamplers[0].wrapT, nodes, links)

            if color0_node_alpha is not None and props.blendMode == 'full':
                rgbMath_node1 = nodes.new("ShaderNodeVectorMath")
                rgbMath_node1.name = ("Alpha0 Mix")
                rgbMath_node1.operation = 'MULTIPLY'
                rgbMath_node1.location = (-225, 0)

                links.new(color0_node_alpha, rgbMath_node1.inputs[1])
                links.new(rgbMath_node1.outputs['Vector'], shaderMix_node.inputs['Fac'])
            
            elif props.blendMode == 'full':
                links.new(texNode0.outputs['Alpha'], shaderMix_node.inputs['Fac'])

            if len(validSamplers) == 1:
                links.new(texNode0.outputs['Color'], rgbMath_node0.inputs[0])

                if props.blendMode == 'full':
                    links.new(texNode0.outputs['Alpha'], rgbMath_node1.inputs[0])
                else:
                    links.new(texNode0.outputs['Alpha'], shaderMix_node.inputs['Fac'])

            if len(validSamplers) == 2:
                texNode1 = nodes.get("TEX1")

                rgbMath_node2 = nodes.new("ShaderNodeVectorMath")
                rgbMath_node2.name = ("Color1 Mix")
                rgbMath_node3 = nodes.new("ShaderNodeVectorMath")
                rgbMath_node3.name = ("Alpha1 Mix")
                mapping2_node = nodes.new("ShaderNodeMapping")
                uvmap2_node = nodes.new("ShaderNodeUVMap")
                uvmap2_node.uv_map = "UVMap.001"

                texNode1.location = (-750, 300)
                texNode0.location = (-750, 0)
                rgbMath_node2.location = (-450, 300)
                rgbMath_node3.location = (-450, 0)
                mapping2_node.location = (mapping_node.location.x, (mapping_node.location.y + 500))
                uvmap2_node.location = (uvmap_node.location.x,(uvmap_node.location.y + 500))
                
                samplerWrapPreview(texNode1, validSamplers[1].wrapS, validSamplers[1].wrapT, nodes, links)

                links.new(texNode0.outputs['Color'], rgbMath_node2.inputs[0])
                links.new(texNode1.outputs['Color'], rgbMath_node2.inputs[1])
                links.new(texNode0.outputs['Alpha'], rgbMath_node3.inputs[0])
                links.new(texNode1.outputs['Alpha'], rgbMath_node3.inputs[1])
                links.new(rgbMath_node2.outputs['Vector'], rgbMath_node0.inputs[0])
                if props.blendMode == 'full':
                    links.new(rgbMath_node3.outputs['Vector'], rgbMath_node1.inputs[0])
                else:
                    links.new(rgbMath_node3.outputs['Vector'], shaderMix_node.inputs['Fac'])
            elif len(validSamplers) > 2:
                print(f"more than two samplers found on:{data.name}: {len(validSamplers)}")             

            links.new(finalShader, output_shader_input)

        mats.append(matEmpty)
    
    scene = bpy.context.scene
    master_collection = scene.collection

    mat_collection = bpy.data.collections.get("Materials")

    if mat_collection is None:
        mat_collection = bpy.data.collections.new("Materials")
        master_collection.children.link(mat_collection)

    for i, mat in enumerate(mats):
        mat_collection.objects.link(mat)

    return materials

    #TODO: implement non-(2, 2)-mirror math

def samplerWrapPreview(texNode, S, T, nodes, links):

    if texNode.name == "TEX0":
        mapping_node = nodes.get("Mapping")            
        uv_node = nodes.get("UV Map")

        if (S == 0) and (T == 0):
            texNode.extension = 'CLIP'
            links.new(uv_node.outputs[0], mapping_node.inputs[0])
            links.new(mapping_node.outputs[0], texNode.inputs[0])
        elif (S == 1) and (T == 1):
            texNode.extension = 'REPEAT' #already default, just cleaner to include for ref. for later logic
            links.new(uv_node.outputs[0], mapping_node.inputs[0])
            links.new(mapping_node.outputs[0], texNode.inputs[0])
        elif (S == 2) and (T == 2):
            texNode.extension = 'MIRROR'
            links.new(uv_node.outputs[0], mapping_node.inputs[0])
            links.new(mapping_node.outputs[0], texNode.inputs[0])
        else:
            clampPrep(S, T, nodes, links, uv_node, texNode, mapping_node, None)

    if texNode.name == "TEX1":
        mapping2_node = nodes.get("Mapping.001")
        uv2_node = nodes.get("UV Map.001")
        if (S == 0) and (T == 0):
            texNode.extension = 'CLIP'
            links.new(uv2_node.outputs[0], mapping2_node.inputs[0])
            links.new(mapping2_node.outputs[0], texNode.inputs[0])
        elif (S == 1) and (T == 1):
            texNode.extension = 'REPEAT' #already default, just cleaner to include for ref. for later logic
            links.new(uv2_node.outputs[0], mapping2_node.inputs[0])
            links.new(mapping2_node.outputs[0], texNode.inputs[0])
        elif (S == 2) and (T == 2):
            texNode.extension = 'MIRROR'
            links.new(uv2_node.outputs[0], mapping2_node.inputs[0])
            links.new(mapping2_node.outputs[0], texNode.inputs[0])

        else:
            clampPrep(S, T, nodes, links, uv2_node, texNode, None, mapping2_node)

def clampPrep(S, T, nodes, links, uv_node, tex, mapping=None, mapping2=None):
    if mapping2 is None and mapping:
        sepXYZ = nodes.new("ShaderNodeSeparateXYZ")
        comXYZ = nodes.new("ShaderNodeCombineXYZ")

        sepXYZ.location = ((mapping.location.x - 650), (mapping.location.y - 150))
        comXYZ.location = ((mapping.location.x - 250), (mapping.location.y - 150))

        uv_node.location = ((sepXYZ.location.x - 200), mapping.location.y)

        clampMath(S, T, nodes, links, uv_node, sepXYZ, comXYZ, mapping, tex)

    if mapping is None and mapping2:
        sepXYZ2 = nodes.new("ShaderNodeSeparateXYZ")
        comXYZ2 = nodes.new("ShaderNodeCombineXYZ")

        sepXYZ2.location = ((mapping2.location.x - 650), mapping2.location.y)
        comXYZ2.location = ((mapping2.location.x - 250), mapping2.location.y)

        uv_node.location = ((sepXYZ2.location.x - 200), mapping2.location.y)

        clampMath(S, T, nodes, links, uv_node, sepXYZ2, comXYZ2, mapping2, tex)

def clampMath(S, T, nodes, links, uv_node, sepXYZ, comXYZ, mapping, tex):
    links.new(uv_node.outputs['UV'], sepXYZ.inputs['Vector'])
    links.new(sepXYZ.outputs[2], comXYZ.inputs[2]) #presumably Z will always be 0, unsure if should be connected
    links.new(comXYZ.outputs['Vector'], mapping.inputs[0])

    # Default repeat connection
    if S == 1:
        links.new(sepXYZ.outputs[0], comXYZ.inputs[0])
        links.new(mapping.outputs[0], tex.inputs[0])
    if T == 1:
        links.new(sepXYZ.outputs[1], comXYZ.inputs[1])
        links.new(mapping.outputs[0], tex.inputs[0])
    
    #Clamp connection
    if S == 0:
        clamp_node = nodes.new("ShaderNodeClamp")
        clamp_node.location = ((sepXYZ.location.x + 200), sepXYZ.location.y + 200)

        links.new(sepXYZ.outputs[0], clamp_node.inputs['Value'])
        links.new(clamp_node.outputs[0], comXYZ.inputs[0])
        links.new(mapping.outputs[0], tex.inputs[0])

    if T == 0:
        clamp_node = nodes.new("ShaderNodeClamp")
        clamp_node.location = ((sepXYZ.location.x + 200), sepXYZ.location.y - 200)

        links.new(sepXYZ.outputs[1], clamp_node.inputs['Value'])
        links.new(clamp_node.outputs[0], comXYZ.inputs[1])
        links.new(mapping.outputs[0], tex.inputs[0])