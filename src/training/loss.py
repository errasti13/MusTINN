from src.physics.steadyNS import NavierStokes2D, NavierStokes3D
import tensorflow as tf
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

class NavierStokesLoss:

    def __init__(self, mesh, model):
        self.mesh    = mesh
        self.model   = model

        self.physicsLoss = NavierStokes2D() if mesh.is2D else NavierStokes3D()

        self.loss = None

        self.nu = 0.01

    def loss_function(self):
        if self.mesh.is2D:
            return self.loss_function2D()
        else:
            raise NotImplementedError("Only 2D loss functions are implemented for now.")

    def loss_function2D(self):
        X = tf.reshape(tf.convert_to_tensor(self.mesh.X, dtype=tf.float32), [-1, 1])
        Y = tf.reshape(tf.convert_to_tensor(self.mesh.Y, dtype=tf.float32), [-1, 1])

        total_loss = 0

        with tf.GradientTape(persistent=True) as tape:
            tape.watch([X, Y])

            # Compute predictions
            uvp_pred = self.model.model(tf.concat([X, Y], axis=1))
            u_pred = uvp_pred[:, 0]
            v_pred = uvp_pred[:, 1]
            p_pred = uvp_pred[:, 2]

            # Compute first derivatives
            u_x = tape.gradient(u_pred, X)
            u_y = tape.gradient(u_pred, Y)
            v_x = tape.gradient(v_pred, X)
            v_y = tape.gradient(v_pred, Y)
            p_x = tape.gradient(p_pred, X)
            p_y = tape.gradient(p_pred, Y)

        # Compute second derivatives manually
        u_xx = tf.gradients(u_x, X)[0]
        u_yy = tf.gradients(u_y, Y)[0]
        v_xx = tf.gradients(v_x, X)[0]
        v_yy = tf.gradients(v_y, Y)[0]

        continuity = u_x + v_y
        momentum_u = u_pred * u_x + v_pred * u_y + p_x - self.nu * (u_xx + u_yy)
        momentum_v = u_pred * v_x + v_pred * v_y + p_y - self.nu * (v_xx + v_yy)

        f_loss_u = tf.reduce_mean(tf.square(momentum_u))
        f_loss_v = tf.reduce_mean(tf.square(momentum_v))
        continuity_loss = tf.reduce_mean(tf.square(continuity))

        total_loss += f_loss_u + f_loss_v + continuity_loss

        # Compute boundary condition losses
        for boundary_key, boundary_data in self.mesh.boundaries.items():
            xBc = boundary_data['x']
            yBc = boundary_data['y']
            uBc = boundary_data['u']
            vBc = boundary_data['v']
            pBc = boundary_data['p']

            xBc = self.convert_and_reshape(xBc)
            yBc = self.convert_and_reshape(yBc)
            uBc_tensor, vBc_tensor, pBc_tensor = self.imposeBoundaryCondition(uBc, vBc, pBc)

            # Compute boundary losses for each condition
            uBc_loss, vBc_loss, pBc_loss = self.computeBoundaryLoss(self.model.model, xBc, yBc, uBc_tensor, vBc_tensor, pBc_tensor)
            
            total_loss += uBc_loss + vBc_loss + pBc_loss

        return total_loss


    
    def convert_and_reshape(self, tensor, dtype=tf.float32, shape=(-1, 1)):
                        if tensor is not None:
                            return tf.reshape(tf.convert_to_tensor(tensor, dtype=dtype), shape)
                        return None
       
    def imposeBoundaryCondition(self, uBc, vBc, pBc):
        def convert_if_not_none(tensor):
            return tf.convert_to_tensor(tensor, dtype=tf.float32) if tensor is not None else None

        uBc = convert_if_not_none(uBc)
        vBc = convert_if_not_none(vBc)
        pBc = convert_if_not_none(pBc)

        return uBc, vBc, pBc
    
    def computeBoundaryLoss(self, model, xBc, yBc, uBc, vBc, pBc):
        def compute_loss(bc, idx):
            if bc is not None:
                pred = model(tf.concat([tf.cast(xBc, dtype=tf.float32), tf.cast(yBc, dtype=tf.float32)], axis=1))[:, idx]
                return tf.reduce_mean(tf.square(pred - bc))
            else:
                return tf.constant(0.0)

        uBc_loss = compute_loss(uBc, 0)
        vBc_loss = compute_loss(vBc, 1)
        pBc_loss = compute_loss(pBc, 2)

        return uBc_loss, vBc_loss, pBc_loss