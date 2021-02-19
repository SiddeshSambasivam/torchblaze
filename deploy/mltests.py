import torch
import torch.nn as nn
import torch.nn.functional as F


class ParamsTooLargeException(Exception):
    pass


class ParamsTooSmallException(Exception):
    pass


class GradientAboveThresholdException(Exception):
    pass


class NaNParamsException(Exception):
    pass


class InfParamsException(Exception):
    pass


class GradientsUninitializedException(Exception):
    pass


def get_params(model):
    """Retrieves list of all the named parameters in a model.

    Arguments:
        model::torch.nn.Module- Ideally the deep learning model, but can be a set of layers/layer too.

    Returns:
        param_list::list- List of all the named parameters in the model.
    """
    return [(name, params) for name, params in model.named_parameters() if params.requires_grad]


def check_nan(name, params):
    """Tests for the presence of NaN values [torch.tensor(float("nan"))] in the given tensor of model parameter.

    Arguments:
        name::str- Name of the parameter
        params::torch.Tensor- Trainable named parameters associated with a layer

    Returns:
        None- Throws an exception in case any parameter is a NaN value.
    """
    try:
        assert not params.isnan().any()
    except AssertionError:
        raise NaNParamsException(f"\nNaN values found in the layer: {name}")


def check_infinite(name, params):
    """Tests for the presence of infinite values [torch.tensor(float("Inf"))] in the given tensor of model parameter.

    Arguments:
        name::str- Name of the parameter
        params::torch.Tensor- Trainable named parameters associated with a layer

    Returns:
        None- Throws an exception in case any parameter is a Inf value.
    """
    try:
        assert not params.isinf().any()
    except AssertionError:
        raise InfParamsException(
            f"\nInfinite values found in the layer: {name}")


def check_smaller(name, params, upper_limit=0):
    """Tests if the absolute value of any parameter exceeds a certain threshold.

    Arguments:
        name::str- Name of the parameter
        params::torch.Tensor- Trainable named parameters associated with a layer
        upper_limit::float- The threshold value every parameter should be smaller than in terms of its absolute value.

    Returns:
        None- Throws an exception in case any parameter is a exceeds threshold value.
    """
    try:
        assert params.abs().less(upper_limit).any()
    except AssertionError:
        raise ParamsTooLargeException(
            f"\nCertain parameters in layer '{name}' found to be greater than the threshold value = {upper_limit}.")


def check_greater(name, params, lower_limit=0):
    """Tests if the absolute value of any parameter falls below a certain threshold.

    Arguments:
        name::str- Name of the parameter
        params::torch.Tensor- Trainable named parameters associated with a layer
        lower_limit::float- The threshold value every parameter should be greater than in terms of its absolute value.

    Returns:
        None- Throws an exception in case any parameter is a NaN value.
    """
    try:
        assert params.abs().greater(lower_limit).any()
    except AssertionError:
        raise ParamsTooSmallException(
            f"\nCertain parameters in layer '{name}' found to be smaller than the threshold value = {lower_limit}.")


def check_gradient_smaller(name, params, grad_limit=1e3):
    """Tests if the absolute gradient value for any parameter exceed a certain threshold. Can be used to check for gradient explosion.

    Arguments:
        name::str- Name of the parameter
        params::torch.Tensor- Trainable named parameters associated with a layer
        grad_limit::float- A threshold value, such that, |params.grad| < grad_limit

    Returns:
        None- Throws an exception in case the gradient for any parameter exceeds the threshold value (grad_limit)
        OR
        None- Throws an exception in case the method is used without running the loss.backward() method for backprop.
    """
    grads = params.grad
    try:
        assert not (grads == None)
    except AssertionError:
        raise GradientsUninitializedException("\nModel gradients not initialized. Kindly run loss.backwards() to initialize gradients first.")

    try:
        assert not grads.abs().greater(grad_limit).any()
    except AssertionError:
        raise GradientAboveThresholdException(f"\nGradients (absolute) for certain parameters in layer '{name}' found to be greater than the threshold grad_limit value = {grad_limit}.")


def model_test(model, batch_x, batch_y, optim_fn,
               loss_fn=torch.nn.CrossEntropyLoss(), epochs=5, 
               test_gradient_smaller=True, test_greater=True,
               test_smaller=True, test_infinite=True, test_nan=True,
               upper_limit=1e-1, lower_limit=1e-2, grad_limit=1e4):
    """Executes a suite of tests on the ML model.
    Set <test_name> = False if you want to exclude a certain test from the test suite.

    Arguments:
        model::nn.Module- The model that you want to test.

        batch_x::torch.Tensor- A single batch of data features to perform model checks

        batch_y::torch.Tensor- A single batch of data labels to perform model checks

        optim::torch.optim- default=torch.optim.Adam, Optimizer algorithm to be used during model training 

        loss_fn- default=torch.nn.CrossEntropyLoss, Loss function to be used for model evaluation during training

        test_gradient_smaller::bools- default=True, Asserts if gradients exceed a certain threshold  

        test_greater::bools- default=True, Asserts if all parameters > threshold limit

        test_smaller::bools- default=True, Asserts if all parameters < threshold limit

        test_infinite::bools- default=True, Asserts that no parameters == infinite

        test_nan::bools- default=True, Asserts that no parameters == NaN

        upper_limit::float- default=1e2, Absolute value of all parameters should be smaller than this threshold value

        lower_limit::float- default=1e-2, Absolute value of all parameters should be greater than this threshold value

        grad_limit::float- default=1e4, Absolute value of all gradients should be smaller than this threshold value
    """
    model.train() # putting the model in training mode
    for epoch in range(epochs): 
        optim_fn.zero_grad()
        output = model(batch_x)
        loss = loss_fn(output, batch_y)
        loss.backward()
        optim_fn.step()

        model_params = get_params(model) # getting list of model parameters
        for name, params in model_params:
            if test_greater:
                check_greater(name, params, lower_limit=lower_limit)
            if test_smaller:
                check_smaller(name, params, upper_limit=upper_limit)
            if test_gradient_smaller:
                check_gradient_smaller(name, params, grad_limit=grad_limit)
            if test_nan:
                check_nan(name, params)
            if test_infinite:
                check_infinite(name, params)
        
        print(f"Epoch {epoch}: All tests passed successfully.")
            
            

if __name__ == "__main__":
    class Net(nn.Module):
        def __init__(self):
            super(Net, self).__init__()
            self.conv1 = nn.Conv2d(3, 6, 5)
            self.pool = nn.MaxPool2d(2, 2)
            self.conv2 = nn.Conv2d(6, 16, 5)
            self.fc1 = nn.Linear(16 * 5 * 5, 120)
            self.fc2 = nn.Linear(120, 84)
            self.fc3 = nn.Linear(84, 10)

        def forward(self, x):
            x = self.pool(F.relu(self.conv1(x)))
            x = self.pool(F.relu(self.conv2(x)))
            x = x.view(-1, 16 * 5 * 5)
            x = F.relu(self.fc1(x))
            x = F.relu(self.fc2(x))
            x = self.fc3(x)
            return x

    net = Net()

    x = torch.randn(4,3,32,32)
    y = torch.randint(low=0, high=10, size=(4,))

    criterion = torch.nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(net.parameters(), lr=0.001, momentum=0.9)

    model_test(model=net, batch_x=x, batch_y=y, optim_fn=optimizer, loss_fn=criterion)

    