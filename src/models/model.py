import tensorflow as tf
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

class PINN:
    def __init__(self, input_shape=2, output_shape=1, layers=[20, 20, 20], activation='tanh', learning_rate=0.01, eq = 'LidDrivenCavity'):
        self.model = self.create_model(input_shape, output_shape, layers, activation)
        self.model.summary()
        self.optimizer = tf.keras.optimizers.Adam(learning_rate=self.learning_rate_schedule(learning_rate))

        self.eq = eq


    def create_model(self, input_shape,  output_shape, layers, activation):
        model = tf.keras.Sequential()
        model.add(tf.keras.layers.InputLayer(input_shape=input_shape))
        for units in layers:
            model.add(tf.keras.layers.Dense(units, activation=activation))
        model.add(tf.keras.layers.Dense(output_shape))  # Output layer
        return model

    def learning_rate_schedule(self, initial_learning_rate):
        return tf.keras.optimizers.schedules.ExponentialDecay(
            initial_learning_rate=initial_learning_rate,
            decay_steps=1000,
            decay_rate=0.9
        )

    @tf.function
    def train_step(self, loss_function):
        with tf.GradientTape() as tape:
            loss = loss_function()  # Call the loss function here to compute the loss
        gradients = tape.gradient(loss, self.model.trainable_variables)
        self.optimizer.apply_gradients(zip(gradients, self.model.trainable_variables))
        return loss

    def train(self, loss_function, epochs, print_interval, autosave_interval):
        loss_history = []
        epoch_history = []

        plt.ion()
        fig, ax = plt.subplots()
        ax.set_xlabel('Epoch')
        ax.set_ylabel('Loss')
        ax.set_yscale('log')  

        ax.yaxis.set_major_formatter(ScalarFormatter())
        ax.yaxis.set_minor_formatter(ScalarFormatter())
        ax.yaxis.get_major_formatter().set_useOffset(False)
        ax.yaxis.get_major_formatter().set_scientific(False)

        line, = ax.semilogy([], [], label='Training Loss')
        plt.legend()

        for epoch in range(epochs):
            loss = self.train_step(loss_function)

            if (epoch + 1) % print_interval == 0:
                loss_history.append(loss.numpy())
                epoch_history.append(epoch + 1)

                line.set_xdata(epoch_history)
                line.set_ydata(loss_history)
                ax.relim()  
                ax.autoscale_view() 

                plt.draw()
                plt.pause(0.001)

                print(f"Epoch {epoch + 1}: Loss = {loss.numpy()}")

            if (epoch + 1) % autosave_interval == 0:
                self.model.save(f'trainedModels/{self.eq}.tf')

        plt.ioff()  # Turn off interactive mode
        plt.close()

    def predict(self, X):
        return self.model.predict(X)