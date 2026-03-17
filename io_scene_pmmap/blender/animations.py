import bpy #type: ignore
import math

def _track_display_name(t) -> str:
    # Works for joint/material/light tracks
    return (
        getattr(t, "target_name", None)
        or getattr(t, "material_name", None)
        or getattr(t, "light_name", None)
        or "???"
    )

def build_anims_from_scene(data, matprefix="", context=None):
    animContainers = []

    scene = bpy.context.scene if context is None else context.scene
    master_collection = scene.collection

    anim_collection = bpy.data.collections.get("Animations")
    if anim_collection is None:
        anim_collection = bpy.data.collections.new("Animations")
        master_collection.children.link(anim_collection)

    for anim_idx, bundle in enumerate(data.values):
        animCont = bpy.data.objects.new(f"{bundle.name} [{anim_idx}]", None)
        tracks = None

        idProp = animCont.ttyd_world_empty
        idProp.isAnimation = True

        animProps = animCont.ttyd_world_animation
        animProps.name = bundle.name
        animProps.length = bundle.lengthFrames

        # Create NLA + table entries for each table type that exists
        if bundle.joint is not None:
            animProps.joint = True
            tracks = bundle.joint.tracks
            jointTable = animProps.joint_table
            jointTable.count = len(tracks)
            traType = "JNT"

            for i, track in enumerate(tracks):
                trackName = _track_display_name(track)
                blenderTrack = jointTable.tracks.add()
                blenderTrack.name = f"{matprefix}{trackName}"
                joint = blenderTrack.joint = bpy.data.objects.get(f"{matprefix}{trackName}")
                if joint is None:
                    print(f"[WARNING]: No joint object found for track {trackName} in animation {bundle.name}. Skipping.")
                    continue

                blenderTrack.keyframeCount = len(track.keyframes)

                obj_origin = joint.location
                anim_origin = [track.anim_origin.x, track.anim_origin.y, track.anim_origin.z]
                anim_scale = [track.anim_scale.x, track.anim_scale.y, track.anim_scale.z]
                anim_delta = [track.obj_pos_delta.x, track.obj_pos_delta.y, track.obj_pos_delta.z]
                joint.ttyd_attributes.anim_origin = (track.anim_origin.x, track.anim_origin.y, track.anim_origin.z)
                joint.ttyd_attributes.origin_offset = blenderTrack.anim_delta = (anim_delta[0], anim_delta[1], anim_delta[2])

                action = make_transform_action(traType, i, joint, obj_origin, anim_origin, anim_scale, anim_delta, trackName, track)
                blenderTrack.action = action

        if bundle.mat_uv is not None:
            animProps.uv = True
            tracks = bundle.mat_uv.tracks
            uvTable = animProps.uv_table
            uvTable.count = len(tracks)

            for i, track in enumerate(tracks):
                trackName = _track_display_name(track)    
                blenderTrack = uvTable.tracks.add()
                blenderTrack.name = f"{matprefix}{trackName}"
                samplerIndex = blenderTrack.samplerIndex = track.samplerIndex

                mat = blenderTrack.mat = bpy.data.objects.get(f"{matprefix}{trackName}")
                mat_v = blenderTrack.mat_v = bpy.data.objects.get(f"{matprefix}{trackName}_v")
                mat_v_x = blenderTrack.mat_v_x = bpy.data.objects.get(f"{matprefix}{trackName}_v_x")

                blenderTrack.skew = (track.skewX, track.skewY)

                if mat:
                    emptyProps = mat.ttyd_world_material
                    for ref in emptyProps.materialRefs: #iterates through all preview mats
                        drawMat = ref.material
                        action = make_matuv_action(i, drawMat, samplerIndex, trackName, track)
                        if blenderTrack.action is None:
                            blenderTrack.action = action

                if mat_v:
                    emptyProps = mat_v.ttyd_world_material
                    for ref in emptyProps.materialRefs: #iterates through all preview mats
                        drawMat = ref.material
                        action = make_matuv_action(i, drawMat, samplerIndex, trackName, track)
                        if blenderTrack.action is None:
                            blenderTrack.action = action

                if mat_v_x:
                    emptyProps = mat_v_x.ttyd_world_material
                    for ref in emptyProps.materialRefs: #iterates through all preview mats
                        drawMat = ref.material
                        action = make_matuv_action(i, drawMat, samplerIndex, trackName, track)
                        if blenderTrack.action is None:
                            blenderTrack.action = action

                if blenderTrack.action is None:
                    dummy = make_matuv_action(i, None, samplerIndex, trackName, track)
                    blenderTrack.action = dummy

        if bundle.mat_alpha is not None:
            animProps.alpha = True
            tracks = bundle.mat_alpha.tracks
            alphaTable = animProps.alpha_table
            alphaTable.count = len(tracks)

            for i, track in enumerate(tracks):
                trackName = _track_display_name(track)    
                blenderTrack = alphaTable.tracks.add()
                blenderTrack.name = f"{matprefix}{trackName}"

                mat = blenderTrack.mat = bpy.data.objects.get(f"{matprefix}{trackName}")
                mat_v = blenderTrack.mat_v = bpy.data.objects.get(f"{matprefix}{trackName}_v")
                mat_v_x = blenderTrack.mat_v_x = bpy.data.objects.get(f"{matprefix}{trackName}_v_x")

                #NOTE: these still need to be tested for validity before blender prev-versions can be made for refMats

                if mat:
                    emptyProps = mat.ttyd_world_material
                    action = make_matalpha_action(i, mat, trackName, track)
                    if blenderTrack.action is None:
                        blenderTrack.action = action

                if mat_v:
                    emptyProps = mat_v.ttyd_world_material
                    action = make_matalpha_action(i, mat_v, trackName, track)
                    if blenderTrack.action is None:
                        blenderTrack.action = action

                if mat_v_x:
                    emptyProps = mat_v_x.ttyd_world_material
                    action = make_matalpha_action(i, mat_v_x, trackName, track)
                    if blenderTrack.action is None:
                        blenderTrack.action = action

                if blenderTrack.action is None:
                    print(f"[WARNING]: No action assigned for {matprefix}{trackName}.\n    Need to implement dummy logic for blend?")


        if bundle.light_xform is not None:
            animProps.lightT = True
            tracks = bundle.light_xform.tracks
            lightTTable = animProps.lightT_table
            lightTTable.count = len(tracks)
            traType = "LIGHT"

            for i, track in enumerate(tracks):
                trackName = _track_display_name(track)
                blenderTrack = lightTTable.tracks.add()
                blenderTrack.name = f"{matprefix}{trackName}"
                light = blenderTrack.light = bpy.data.objects.get(f"{matprefix}{trackName}")

                blenderTrack.keyframeCount = len(track.keyframes)

                #lights don't have these, so use defaults
                obj_origin = [0, 0, 0]
                anim_origin = [0, 0, 0]
                anim_scale = [1, 1, 1]
                anim_delta = [0, 0, 0]

                action = make_transform_action(traType, i, joint, obj_origin, anim_origin, anim_scale, anim_delta, trackName, track)
                blenderTrack.action = action

        if bundle.light_param is not None:
            animProps.lightP = True
            tracks = bundle.light_param.tracks
            lightPTable = animProps.lightP_table
            lightPTable.count = len(tracks)

            for i, track in enumerate(tracks):
                trackName = _track_display_name(track)
                blenderTrack = lightPTable.tracks.add()
                blenderTrack.name = f"{matprefix}{trackName}"
                light = blenderTrack.light = bpy.data.objects.get(f"{matprefix}{trackName}")

                blenderTrack.keyframeCount = len(track.keyframes)

                action = make_lightParam_action(i, light, trackName, track)
                blenderTrack.action = action

        anim_collection.objects.link(animCont)
        animContainers.append(animCont)

    return animContainers

LOC = 1
ROT = 2
SCL = 3

def ensure_fcurve(action, datablock, data_path, index):
    """
    Blender 4.x → action.fcurves.new
    Blender 5.x → action.fcurve_ensure_for_datablock
    """
    if hasattr(action, "fcurve_ensure_for_datablock"):
        return action.fcurve_ensure_for_datablock(
            datablock=datablock,
            data_path=data_path,
            index=index
        )
    else:
        return action.fcurves.new(data_path=data_path, index=index)

def insert_hermite_key(fcu, is_step, time, value, tan_in, tan_out, prev_time=None, next_time=None):
    kp = fcu.keyframe_points.insert(time, value, options={'FAST'})

    # --- Step key ---
    if is_step != 0:
        kp.interpolation = 'CONSTANT'
        return kp

    # --- Hermite (Bezier) key ---
    kp.interpolation = 'BEZIER'
    kp.handle_left_type = 'FREE'
    kp.handle_right_type = 'FREE'

    # Incoming handle
    if prev_time is not None:
        dx_l = (time - prev_time) / 3.0
        kp.handle_left.x = time - dx_l
        kp.handle_left.y = value - tan_in * dx_l
    else:
        kp.handle_left = kp.co

    # Outgoing handle
    if next_time is not None:
        dx_r = (next_time - time) / 3.0
        kp.handle_right.x = time + dx_r
        kp.handle_right.y = value + tan_out * dx_r
    else:
        kp.handle_right = kp.co

    return kp

def build_transform_action_from_dmd(track, obj, obj_origin, anim_origin, anim_scale, anim_delta, action_name):
    action = bpy.data.actions.new(action_name)
    ad = obj.animation_data_create()
    ad.action = action
    # --- Translation ---

    for idx in range(3):
        fcu = ensure_fcurve(action, obj, "location", index=idx)
        keys = track.keyframes

        for i, kf in enumerate(keys):
            prev_t = keys[i-1].time if i > 0 else None
            next_t = keys[i+1].time if i < len(keys)-1 else None

            is_step = kf.translation[idx].bStep

            insert_hermite_key(
                fcu,
                is_step,
                time=kf.time,
                value=kf.translation[idx].value + obj_origin[idx] - anim_origin[idx],
                tan_in=kf.translation[idx].tangentIn,
                tan_out=kf.translation[idx].tangentOut,
                prev_time=prev_t,
                next_time=next_t
            )

    # --- Rotation ---
    for idx in range(3):
        fcu = ensure_fcurve(action, obj, "rotation_euler", index=idx)
        keys = track.keyframes

        for i, kf in enumerate(keys):
            prev_t = keys[i-1].time if i > 0 else None
            next_t = keys[i+1].time if i < len(keys)-1 else None

            value = math.radians(kf.rotation[idx].value)
            tan_in  = math.radians(kf.rotation[idx].tangentIn)
            tan_out = math.radians(kf.rotation[idx].tangentOut)

            is_step = kf.rotation[idx].bStep

            insert_hermite_key(
                fcu,
                is_step,
                time=kf.time,
                value=value,
                tan_in=tan_in,
                tan_out=tan_out,
                prev_time=prev_t,
                next_time=next_t
            )

    # --- Scale ---
    for idx in range(3):
        fcu = ensure_fcurve(action, obj, "scale", index=idx)
        keys = track.keyframes

        for i, kf in enumerate(keys):
            prev_t = keys[i-1].time if i > 0 else None
            next_t = keys[i+1].time if i < len(keys)-1 else None

            sc = kf.scale[idx]
            is_step = sc.bStep

            insert_hermite_key(
                fcu,
                is_step,
                time=kf.time,
                value=sc.value,
                tan_in=sc.tangentIn,
                tan_out=sc.tangentOut,
                prev_time=prev_t,
                next_time=next_t
            )

    return action

def make_transform_action(traType, track_idx, target, obj_origin, anim_origin, anim_scale, anim_delta, trackName, dmd_track):
    animData = target.animation_data_create()

    action = build_transform_action_from_dmd(
        track=dmd_track,
        obj=target,

        obj_origin=obj_origin,
        anim_origin=anim_origin,
        anim_scale=anim_scale,
        anim_delta=anim_delta,
        action_name = f"[{traType}]{target.name}_{trackName}_T{track_idx:03d}"
    )

    nla_track = animData.nla_tracks.new()
    nla_track.name = f"TRANS [{track_idx}] {trackName}"

    strip = nla_track.strips.new(
        name=trackName,
        start=0,
        action=action
    )

    strip.action_frame_start = action.frame_range[0]
    strip.action_frame_end = action.frame_range[1]
    strip.blend_type = 'REPLACE'
    strip.extrapolation = 'HOLD_FORWARD'

    return action

def _get_mapping_node(mat: bpy.types.Material, samplerIndex: int):
    nt = mat.node_tree
    if not nt:
        return

    if samplerIndex == 0:
        return nt.nodes.get("Mapping")
    
    if samplerIndex == 1:
        return nt.nodes.get("Mapping.001")
    
def build_matuv_action_from_dmd(trackName, track, mat: bpy.types.Material, samplerIndex: int, action_name: str):
    nt = mat.node_tree
    if nt is None:
        return None

    mappingNode = _get_mapping_node(mat, samplerIndex)
    if not mappingNode:
        mappingNode = nt.nodes.get("Mapping")
        print(f"[UV] No Mapping nodes found on {trackName}-{mat.name} at index {samplerIndex}. Trying to default to smp 0")
        if not mappingNode:
            print(f"[UV] No Mapping nodes found on {mat.name} with fallback index.")
            return None

    node_name = mappingNode.name

    # Action lives on NodeTree datablock
    ad = nt.animation_data_create()
    action = bpy.data.actions.new(action_name)
    ad.action = action

    def fcurve(socket_index: int, component_index: int):
        path = f'nodes["{node_name}"].inputs[{socket_index}].default_value'
        return ensure_fcurve(action, nt, path, component_index)

    f_loc_x = fcurve(LOC, 0)
    f_loc_y = fcurve(LOC, 1)
    f_rot_z = fcurve(ROT, 2)
    f_scl_x = fcurve(SCL, 0)
    f_scl_y = fcurve(SCL, 1)

    keys = track.keyframes

    def _t(i):  # time helper (optionally quantize)
        return float(keys[i].time)

    for i, kf in enumerate(keys):
        prev_t = _t(i-1) if i > 0 else None
        next_t = _t(i+1) if i < len(keys)-1 else None
        t = _t(i)

        # --- Translation ---
        # Prefer structured arrays if you have them; fallback to translationX/Y objects
        tx = getattr(kf, "translationX", None)
        ty = getattr(kf, "translationY", None)

        insert_hermite_key(
            f_loc_x,
            is_step=getattr(tx, "bStep", 0),
            time=t,
            value=float(tx.value),
            tan_in=float(tx.tangentIn),
            tan_out=float(tx.tangentOut),
            prev_time=prev_t,
            next_time=next_t,
        )
        insert_hermite_key(
            f_loc_y,
            is_step=getattr(ty, "bStep", 0),
            time=t,
            value=float(ty.value),
            tan_in=float(ty.tangentIn),
            tan_out=float(ty.tangentOut),
            prev_time=prev_t,
            next_time=next_t,
        )

        # --- Scale ---
        sx = getattr(kf, "scaleX", None)
        sy = getattr(kf, "scaleY", None)

        insert_hermite_key(
            f_scl_x,
            is_step=getattr(sx, "bStep", 0),
            time=t,
            value=float(sx.value),
            tan_in=float(sx.tangentIn),
            tan_out=float(sx.tangentOut),
            prev_time=prev_t,
            next_time=next_t,
        )
        insert_hermite_key(
            f_scl_y,
            is_step=getattr(sy, "bStep", 0),
            time=t,
            value=float(sy.value),
            tan_in=float(sy.tangentIn),
            tan_out=float(sy.tangentOut),
            prev_time=prev_t,
            next_time=next_t,
        )

        # --- Rotation Z (degrees -> radians, tangents too) ---
        rz = getattr(kf, "rotateZ", None)

        insert_hermite_key(
            f_rot_z,
            is_step=getattr(rz, "bStep", 0),
            time=t,
            value=math.radians(float(rz.value)),
            tan_in=math.radians(float(rz.tangentIn)),
            tan_out=math.radians(float(rz.tangentOut)),
            prev_time=prev_t,
            next_time=next_t,
        )

    return action

def make_matuv_action(track_idx, mat: bpy.types.Material, samplerIndex, trackName, dmd_track):
    if (mat == None):
        mat = bpy.data.materials.new(f"[{trackName}]-dummyAnimHandler")
        mat.use_nodes = True
        mat.use_fake_user = True
        mat.node_tree.nodes.new("ShaderNodeMapping")
    
    nt = mat.node_tree
    if nt is None:
        return

    ad = nt.animation_data_create()

    action = build_matuv_action_from_dmd(
        trackName=trackName,
        track=dmd_track,
        mat=mat,
        samplerIndex=samplerIndex,
        action_name=f"[UV]{mat.name}_{trackName}_T{track_idx:03d}"
    )
    if action is None:
        return

    nla_track = ad.nla_tracks.new()
    nla_track.name = f"UV [{track_idx}] {trackName}"

    strip = nla_track.strips.new(name=action.name, start=0, action=action)
    strip.action_frame_start = action.frame_range[0]
    strip.action_frame_end   = action.frame_range[1]
    strip.blend_type = 'REPLACE'
    strip.extrapolation = 'HOLD_FORWARD'

    return action

def build_matalpha_action_from_dmd(track, emptyMat, blend, action_name: str):
    ad = emptyMat.animation_data_create()
    action = bpy.data.actions.new(action_name)
    ad.action = action

    for idx in range(4):
        fcu = ensure_fcurve(action, emptyMat, "ttyd_world_material.blendAlphaModulationR", index=idx)
        keys = track.keyframes

        for i, kf in enumerate(keys):
            prev_t = keys[i-1].time if i > 0 else None
            next_t = keys[i+1].time if i < len(keys)-1 else None

            is_step = kf.rgba[idx].bStep

            insert_hermite_key(
                fcu,
                is_step,
                time=kf.time,
                value=kf.rgba[idx].value,
                tan_in=kf.rgba[idx].tangentIn,
                tan_out=kf.rgba[idx].tangentOut,
                prev_time=prev_t,
                next_time=next_t
            )

    return action
    
def make_matalpha_action(track_idx, emptyMat, trackName, dmd_track):
    matProps = emptyMat.ttyd_world_material
    aBMR = matProps.blendAlphaModulationR

    ad = emptyMat.animation_data_create()

    action = build_matalpha_action_from_dmd(
        track=dmd_track,
        emptyMat=emptyMat,
        blend=aBMR,
        action_name=f"[BLEND]{emptyMat.name}_{trackName}_T{track_idx:03d}"
    )

    nla_track = ad.nla_tracks.new()
    nla_track.name = f"BLEND [{track_idx}] {trackName}"

    strip = nla_track.strips.new(
        name=trackName,
        start=0,
        action=action
    )

    strip.action_frame_start = action.frame_range[0]
    strip.action_frame_end = action.frame_range[1]
    strip.blend_type = 'REPLACE'
    strip.extrapolation = 'HOLD_FORWARD'

    return action

def make_lightParam_action(track_idx, light, trackName, dmd_track):
    ad = light.animation_data_create()

    action = build_lightparam_action_from_dmd(
        track=dmd_track,
        light=light,
        action_name=f"[PARAM]{light.name}_{trackName}_T{track_idx:03d}"
    )
    if action is None:
        return

    nla_track = ad.nla_tracks.new()
    nla_track.name = f"PARAM [{track_idx}] {trackName}"

    strip = nla_track.strips.new(name=action.name, start=1, action=action)
    strip.action_frame_start = action.frame_range[0]
    strip.action_frame_end   = action.frame_range[1]
    strip.blend_type = 'REPLACE'
    strip.extrapolation = 'HOLD_FORWARD'

    return action

def build_lightparam_action_from_dmd(track, light, action_name):
    props = light.ttyd_world_light

    ad = light.animation_data_create()
    action = bpy.data.actions.new(action_name)
    ad.action = action

    keys = track.keyframes

    for idx in range(3):
        fcu = ensure_fcurve(action, light, "ttyd_world_light.multiplier", index=idx)

        for i, kf in enumerate(keys):
            prev_t = keys[i-1].time if i > 0 else None
            next_t = keys[i+1].time if i < len(keys)-1 else None

            is_step = kf.color[idx].bStep

            insert_hermite_key(
                fcu,
                is_step,
                time=kf.time,
                value=kf.color[idx].value,
                tan_in=kf.color[idx].tangentIn,
                tan_out=kf.color[idx].tangentOut,
                prev_time=prev_t,
                next_time=next_t
            )

     # --- Spot angle (scalar) ---
    fcu_spot = ensure_fcurve(action, light, "ttyd_world_light.spotAngle", index=0)

    for i, kf in enumerate(keys):
        prev_t = keys[i-1].time if i > 0 else None
        next_t = keys[i+1].time if i < len(keys)-1 else None

        is_step = kf.spotAngle.bStep

        insert_hermite_key(
            fcu_spot,
            is_step,
            time=kf.time,
            value=kf.spotAngle.value,
            tan_in=kf.spotAngle.tangentIn,
            tan_out=kf.spotAngle.tangentOut,
            prev_time=prev_t,
            next_time=next_t
        )

    # --- Angular attenuation ---
    fcu_ang = ensure_fcurve(action, light, "ttyd_world_light.angularAttenuation", index=0)

    for i, kf in enumerate(keys):
        prev_t = keys[i-1].time if i > 0 else None
        next_t = keys[i+1].time if i < len(keys)-1 else None

        is_step = kf.angularAttenuation.bStep

        insert_hermite_key(
            fcu_ang,
            is_step,
            time=kf.time,
            value=kf.angularAttenuation.value,
            tan_in=kf.angularAttenuation.tangentIn,
            tan_out=kf.angularAttenuation.tangentOut,
            prev_time=prev_t,
            next_time=next_t
        )

    return action

    