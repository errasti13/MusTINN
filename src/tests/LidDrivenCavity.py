import numpy as np

from src.mesh.mesh import Mesh
from src.models.model import PINN
from src.training.loss import NavierStokesLoss
from src.plot.plot import Plot

class LidDrivenCavity():
    
    def __init__(self, caseName, xRange, yRange):
        self.is2D = True

        self.problemTag = caseName
        self.mesh  = Mesh(self.is2D)
        self.model = PINN(input_shape=2, output_shape=3, eq = self.problemTag, layers=[20,40,60,40,20])

        self.loss = None
        self.Plot = None
        
        self.xRange = xRange
        self.yRange = yRange

        return
    
    def generateMesh(self, Nx=100, Ny=100, NBoundary=100, sampling_method='random'):
        # Initialize boundaries
        self.mesh.boundaries = {
            'left': {'x': None, 'y': None, 'u': None, 'v': None, 'p': None},
            'right': {'x': None, 'y': None, 'u': None, 'v': None, 'p': None},
            'bottom': {'x': None, 'y': None, 'u': None, 'v': None, 'p': None},
            'top': {'x': None, 'y': None, 'u': None, 'v': None, 'p': None}
        }
        
        self.mesh.setBoundary('top',
                    np.linspace(self.xRange[0], self.xRange[1], NBoundary),
                    np.full((NBoundary, 1), self.yRange[1], dtype=np.float32),
                    u = np.ones(NBoundary), v = np.zeros(NBoundary))

        self.mesh.setBoundary('bottom',
                    np.linspace(self.xRange[0], self.xRange[1], NBoundary),
                    np.full((NBoundary, 1), self.yRange[0], dtype=np.float32),
                    u = np.zeros(NBoundary), v = np.zeros(NBoundary))

        self.mesh.setBoundary('left',
                    np.full((NBoundary, 1), self.xRange[0], dtype=np.float32),
                    np.linspace(self.yRange[0], self.yRange[1], NBoundary),
                    u = np.zeros(NBoundary), v = np.zeros(NBoundary))

        self.mesh.setBoundary('right',
                    np.full((NBoundary, 1), self.xRange[1], dtype=np.float32),
                    np.linspace(self.yRange[0], self.yRange[1], NBoundary),
                    u = np.zeros(NBoundary), v = np.zeros(NBoundary))
        
        # Generate the mesh
        self.mesh.generateMesh(
            Nx=Nx,
            Ny=Ny,
            sampling_method=sampling_method
        )
        return
    
    def getLossFunction(self):
        self.loss = NavierStokesLoss(self.mesh, self.model)
    
    def train(self, epochs=10000, print_interval=100,  autosaveInterval=10000):
        self.getLossFunction()
        self.model.train(self.loss.loss_function, epochs=epochs, print_interval=print_interval,autosave_interval=autosaveInterval)

    def predict(self):
        X = (np.hstack((self.mesh.x.flatten()[:, None], self.mesh.y.flatten()[:, None])))
        sol = self.model.predict(X)

        self.mesh.solutions['u'] = sol[:, 0]
        self.mesh.solutions['v'] = sol[:, 1]
        self.mesh.solutions['p'] = sol[:, 2]

        self.generate_plots()  # Generate plots after prediction

        return
    
    def generate_plots(self):
        self.Plot = Plot(self.mesh)

    def plot(self, solkey = 'u', streamlines = False):
        self.Plot.plot(solkey, streamlines)