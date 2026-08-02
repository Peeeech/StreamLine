import bpy #type: ignore
from mathutils import Vector #type: ignore

class MoveActiveWithArrows(bpy.types.Operator):
    bl_idname = "view3d.move_active_with_arrows"
    bl_label = "Move Active Object with Arrows"

    target_name: bpy.props.StringProperty() #type: ignore

    accel = 0.04
    max_speed = 0.5
    multiplier = 1.5
    friction = 0.7
    base_z_scale = 0.5

    def execute(self, context):
        wm = context.window_manager

        if wm.get("camroad_running"):
            self.report({'WARNING'}, "Already running")
            return {'CANCELLED'}

        obj = bpy.data.objects.get(self.target_name)
        if obj is None:
            self.report({'ERROR'}, "Target not found")
            return {'CANCELLED'}
        
        self.velocity = Vector((0, 0, 0))
        self.keys = {
            "LEFT": False,
            "RIGHT": False,
            "UP": False,
            "DOWN": False,
            "Z_UP": False,
            "Z_DOWN": False,

            "CTRL": False,
        }

        # Timer (60 FPS-ish)
        self._timer = wm.event_timer_add(0.016, window=context.window)

        wm["camroad_running"] = True
        wm.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        try:
            obj = bpy.data.objects.get(self.target_name)
            if obj is None:
                return self.cancel(context)

            if event.type == 'ESC':
                return self.cancel(context)

            # --- KEY STATE ---
            if event.type == 'LEFT_ARROW':
                self.keys["LEFT"] = (event.value != 'RELEASE')
            if event.type == 'RIGHT_ARROW':
                self.keys["RIGHT"] = (event.value != 'RELEASE')
            if event.type == 'UP_ARROW':
                self.keys["UP"] = (event.value != 'RELEASE')
            if event.type == 'DOWN_ARROW':
                self.keys["DOWN"] = (event.value != 'RELEASE')
            if event.type == 'SPACE':
                self.keys["Z_UP"] = (event.value != 'RELEASE')
            if event.type == 'LEFT_SHIFT':
                self.keys["Z_DOWN"] = (event.value != 'RELEASE')
                
            self.keys["CTRL"] = event.ctrl
            self.z_scale = self.base_z_scale

            # ONLY update movement on TIMER
            if event.type == 'TIMER':

                accel_vec = Vector((0, 0, 0))

                if self.keys["CTRL"]:
                    self.z_scale = 0.8
                    sprint_mult = 1.5
                else:
                    self.z_scale = self.base_z_scale
                    sprint_mult = 1.0

                if self.keys["LEFT"]:
                    accel_vec.x -= self.accel
                if self.keys["RIGHT"]:
                    accel_vec.x += self.accel
                if self.keys["UP"]:
                    accel_vec.y += self.accel
                if self.keys["DOWN"]:
                    accel_vec.y -= self.accel
                if self.keys["Z_UP"]:
                    accel_vec.z += self.accel * self.z_scale
                if self.keys["Z_DOWN"]:
                    accel_vec.z -= self.accel * self.z_scale

                self.velocity += accel_vec * sprint_mult

                if self.keys["CTRL"]:
                    if self.velocity.length > self.max_speed * self.multiplier:
                        self.velocity = self.velocity.normalized() * self.max_speed * self.multiplier
                else:
                    if self.velocity.length > self.max_speed:
                        self.velocity = self.velocity.normalized() * self.max_speed

                # Apply movement EVERY FRAME
                obj.location += self.velocity

                # Friction
                self.velocity *= self.friction

            return {'RUNNING_MODAL'}

        except ReferenceError:
            return self.cancel(context)

    def cancel(self, context):
        wm = context.window_manager

        wm.event_timer_remove(self._timer)
        wm["camroad_running"] = False

        return {'CANCELLED'}


classes = (MoveActiveWithArrows,)

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except:
            pass

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass