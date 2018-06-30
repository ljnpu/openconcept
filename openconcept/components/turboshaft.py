import numpy as np
from openmdao.api import ExplicitComponent
from openmdao.api import Group


class SimpleTurboshaft(ExplicitComponent):
    """
    A simple turboshaft which generates shaft power consumes fuel
    This model assumes constant power specific fuel consumption (PSFC)

    Input Vars
    ----------
    shaft_power_rating : float
        (scalar, W)
        Rated power of the turboshaft
    throttle: float
        (n vector, dimensionless)
        Engine throttle. Controls power and fuel flow.
        Produces 100% of rated power at throttle = 1
        Should be in range 0 to 1 or slightly above 1

    Output Vars
    -----------
    shaft_power_out : float
        (n vector, W)
    fuel_flow : float
        (n vector, kg/s)
        FUEL FLOW IS NEGATIVE!
    component_cost : float
        (scalar, USD)
    component_weight : float
        (scalar, kg)
    component_sizing_margin : float
        (n vector, dimensionless)


    Options
    -------
    num_nodes : int
        (default 1) Number of analysis points to run (sets vec length)
    psfc : float
        (default 0.6*1.69e-7 kg/W/s)
        Power specific fuel consumption.
        Conversion from lb/hp/hr to kg/W/s is 1.69e-7
    weight_inc : float
        (default 0, kg/W) Weight per unit rated power
        Override this with a reasonable value for your power class
    weight_base : float
        (default 0, kg) Base weight
        This is a bad assumption for most turboshafts
    cost_inc : float
        (default 1.04, USD/W) Nonrecurring cost per unit power
    cost_base : float
        (default 0 USD) Base cost
    """

    def initialize(self):
        # psfc conversion from g/kW/hr to kg/W/s = 2.777e-10
        # psfc conversion from lbfuel/hp/hr to kg/W/s = 1.690e-7
        self.options.declare('num_nodes', default=1, desc='Number of flight/control conditions')
        self.options.declare('psfc', default=0.6 * 1.68965774e-7,
                             desc='power specific fuel consumption')
        self.options.declare('weight_inc', default=0., desc='kg per watt')
        self.options.declare('weight_base', default=0., desc='kg base weight')
        self.options.declare('cost_inc', default=1.04, desc='$ cost per watt')
        self.options.declare('cost_base', default=0., desc='$ cost base')

    def setup(self):
        nn = self.options['num_nodes']
        self.add_input('throttle', desc='Throttle input (Fractional)', shape=(nn,))
        self.add_input('shaft_power_rating', units='W', desc='Rated shaft power')

        psfc = self.options['psfc']
        weight_inc = self.options['weight_inc']
        weight_base = self.options['weight_base']
        cost_inc = self.options['cost_inc']
        cost_base = self.options['cost_base']

        self.add_output('shaft_power_out', units='W', desc='Output shaft power', shape=(nn,))
        self.add_output('fuel_flow', units='kg/s', desc='Fuel flow in (kg fuel / s)', shape=(nn,))
        self.add_output('component_cost', units='USD', desc='Motor component cost')
        self.add_output('component_weight', units='kg', desc='Motor component weight')
        self.add_output('component_sizing_margin', desc='Fraction of rated power', shape=(nn,))

        self.declare_partials('shaft_power_out', 'shaft_power_rating')
        self.declare_partials('shaft_power_out', 'throttle', rows=range(nn), cols=range(nn))

        self.declare_partials('fuel_flow', 'shaft_power_rating')
        self.declare_partials('fuel_flow', 'throttle', rows=range(nn), cols=range(nn))

        self.declare_partials('component_cost', 'shaft_power_rating', val=cost_inc)
        self.declare_partials('component_weight', 'shaft_power_rating', val=weight_inc)
        self.declare_partials('component_sizing_margin', 'throttle',
                              val=1.0 * np.ones(nn), rows=range(nn), cols=range(nn))

    def compute(self, inputs, outputs):
        nn = self.options['num_nodes']
        psfc = self.options['psfc']
        weight_inc = self.options['weight_inc']
        weight_base = self.options['weight_base']
        cost_inc = self.options['cost_inc']
        cost_base = self.options['cost_base']

        a = inputs['throttle']
        b = inputs['shaft_power_rating']
        c = a * b
        outputs['shaft_power_out'] = inputs['throttle'] * inputs['shaft_power_rating']
        outputs['fuel_flow'] = -inputs['throttle'] * inputs['shaft_power_rating'] * psfc
        outputs['component_cost'] = inputs['shaft_power_rating'] * cost_inc + cost_base
        outputs['component_weight'] = inputs['shaft_power_rating'] * weight_inc + weight_base
        outputs['component_sizing_margin'] = inputs['throttle']

    def compute_partials(self, inputs, J):
        nn = self.options['num_nodes']
        psfc = self.options['psfc']
        J['shaft_power_out', 'throttle'] = inputs['shaft_power_rating'] * np.ones(nn)
        J['shaft_power_out', 'shaft_power_rating'] = inputs['throttle']
        J['fuel_flow', 'throttle'] = -inputs['shaft_power_rating'] * psfc * np.ones(nn)
        J['fuel_flow', 'shaft_power_rating'] = -inputs['throttle'] * psfc
