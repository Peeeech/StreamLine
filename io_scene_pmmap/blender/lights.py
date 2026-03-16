try:
    import bpy #type: ignore
    from bpy_extras.io_utils import axis_conversion #type: ignore
except:
    print("no blenda\n")
import math
from mathutils import Matrix, Vector, Euler #type: ignore

#NOTE: we're gonna have to get a little 'hacky' here; DMD light objects may or may not pair closely 1:1 with blender lights, depending on the type of light used.
    # this is because they seemed to have defined the entire light object with universal properties for even lights that don't use position or rotation. so i'm gonna make
    # light objects exist as essentially placeholder empties while figuring out how to tie the custom properties to world properties. this will allow for total visual
    # customization, while preserving easy variable fidelity with the exporter. I'm thinking totally relying on empties as the 'DMD controller', and simply creating the
    # child data for that light based on the TTYD World props

def apply_dmd_light_transform(lightObj, dmdLight):

    loc = Vector((dmdLight.position.x,
                  dmdLight.position.y,
                  dmdLight.position.z))
    rot = Euler((
        math.radians(dmdLight.rotation.x),
        math.radians(dmdLight.rotation.y),
        math.radians(dmdLight.rotation.z),
    ), 'XYZ')
    sca = Vector((dmdLight.scale.x,
                  dmdLight.scale.y,
                  dmdLight.scale.z))

    lightObj.location = loc
    lightObj.rotation_euler = rot
    lightObj.scale = sca

def build_lights_from_scene(lightData, matprefix="", context=None):
    lights = []

    for i, light in enumerate(lightData.values):
        lightName = f"{matprefix}{light.name}" #these could be collapsed into just being called on object creation rather than explicitly typed, but it's more readable this way
        lightType = light.type

        """        This creates an empty for each light, which we'll *eventually* use to set up it's children as the "blender view" version of the light, relying on some VFX tricks.        """
        lightObj = makeDMDLight(lightName, lightType, light) 
        apply_dmd_light_transform(lightObj, light)

        lights.append(lightObj)
    
    try: #blender-spec split
        scene = bpy.context.scene
        master_collection = scene.collection

        light_collection = bpy.data.collections.get("Lights")

        if light_collection is None:
            light_collection = bpy.data.collections.new("Lights")
            master_collection.children.link(light_collection)

        for i, light in enumerate(lights):
            light_collection.objects.link(light)
    except Exception as e:
        print(e)
        return
    
        

def makeDMDLight(name, lightType, light, context=None):
    if context is None:
    #try:
        context = bpy.context
        obj = bpy.data.objects.new(name, None)

        idProp = obj.ttyd_world_empty
        idProp.isLight = True

        props = obj.ttyd_world_light
        props.type = lightType
        props.base_color = (light.color.r, light.color.g, light.color.b, light.color.a)
        props.multiplier = (1, 1, 1, 1)
        props.spotAngle = light.spotAngleFullDegrees
        props.angularAttenuation = light.angularAttenuation
        props.distanceAttenuationType = light.distanceAttenuationType
        props.wFlags = light.wFlags
        props.enableFlags = light.wEnableFlagsIf012d60d8 #named after the var from PistonMiner's (.bt) DMD template

        return obj
    """
        except:
            print(light)"""