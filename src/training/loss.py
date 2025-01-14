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

    def loss_function(self):
        if self.mesh.is2D:
            return self.loss_function2D()
        else:
            raise NotImplementedError("Only 2D loss functions are implemented for now.")

    def loss_function2D(self):
        X = tf.convert_to_tensor(self.mesh.X, dtype=tf.float32)
        Y = tf.convert_to_tensor(self.mesh.Y, dtype=tf.float32)

        X = tf.reshape(X, [-1, 1])
        Y = tf.reshape(Y, [-1, 1])

        with tf.GradientTape(persistent=True) as tape:
            coords = tf.concat([X, Y], axis=1)
            uvp_pred = self.model.model(coords)
            u_pred = uvp_pred[:, 0:1]
            v_pred = uvp_pred[:, 1:2]
            p_pred = uvp_pred[:, 2:3]

            physics_residuals = self.physicsLoss.get_residuals(u_pred, v_pred, p_pred, X, Y)
            continuity_loss = tf.reduce_mean(tf.square(physics_residuals['continuity']))
            momentum_x_loss = tf.reduce_mean(tf.square(physics_residuals['momentum_x']))
            momentum_y_loss = tf.reduce_mean(tf.square(physics_residuals['momentum_y']))

        totalLoss = continuity_loss + momentum_x_loss + momentum_y_loss

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
            
            totalLoss += uBc_loss + vBc_loss + pBc_loss

        return totalLoss

    
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