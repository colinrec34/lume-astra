from .astra import run_astra, run_astra_with_generator, run_astra_with_generator
from .astra_calc import calc_ho_energy_spread
from .tools import full_path
import numpy as np
import json
from inspect import getfullargspec
import os



def end_output_data(output):
    """
    Some outputs are lists. Get the last item. 
    """
    o = {}
    for k in output:
        val = output[k]
        if isinstance(val, str): # Encode strings
            o[k] = val.encode()
        elif np.isscalar(val):
            o[k]=val
        else:
            o['end_'+k]=val[-1]
           
    return o



def default_astra_merit(A):
    """
    merit function to operate on an evaluated LUME-Astra object A. 
    
    Returns dict of scalar values
    """
    # Check for error
    if A.error:
        return {'error':True}
    else:
        m= {'error':False}
    
    # Gather output
    m.update(end_output_data(A.output))
    
    # Load final screen for calc
    A.load_screens(end_only=True)
    screen = A.screen[-1]        
    # TODO: time in screen isn't correct??? 
    m['end_higher_order_energy_spread'] = calc_ho_energy_spread( {'t':screen['z_rel'], 'Energy':(screen['pz_rel'])*1e-3},verbose=False) # eV
    
    # Lost particles have status < -6
    nlost = len(np.where(screen['status'] < -6)[0])    
    m['end_n_particle_loss'] = nlost
    
    # Remove annoying strings
    if 'why_error' in m:
        m.pop('why_error')
    
    
    return m




# Get defaults for **params in evaluate for each type of simulation
def _get_defaults(run_f, extra=None):
    spec = getfullargspec(run_f)
    d = dict(zip(spec.args, spec.defaults))
    d.pop('settings')
    if extra:
        d.update(extra)
    return d





def evaluate(settings, simulation='astra', archive_path=None, merit_f=None, **params):
    """
    Evaluate astra using possible simulations:
        'astra'
        'astra_with_generator'
        'astra_with_distgen'
    
    Returns a flat dict of outputs. 
    
    If merit_f is provided, this function will be used to form the outputs. 
    Otherwise a default funciton will be applied.
    
    Will raise an exception if there is an error. 
    
    """
    
    # Pick simulation to run
    
    if simulation=='astra':
        A = run_astra(settings, **params)

    elif simulation=='astra_with_generator':
        A = run_astra_with_generator(settings, **params)
        
    elif simulation == 'astra_with_distgen':

        # Import here to limit dependency on distgen
        from .astra_distgen import run_astra_with_distgen
        A = run_astra_with_distgen(settings, **params)
        
    else:
        raise 
        
    if merit_f:
        output = merit_f(A)
    else:
        output = default_astra_merit(A)
    
    if output['error']:
        raise
    
    fingerprint = A.fingerprint()
    
    output['fingerprint'] = fingerprint
    
    if archive_path:
        path = full_path(archive_path)
        assert os.path.exists(path), f'archive path does not exist: {path}'
        archive_file = os.path.join(path, fingerprint+'.h5')
        A.archive(archive_file)
        output['archive'] = archive_file
        
    return output


# Convenience wrappers, and their full options

# Get all kwargs from run_astra routines. Save these as the complete set of options
EXTRA = {'archive_path':None, 'merit_f':None}
EXTRA2 = {'archive_path':None, 'merit_f':None, 'distgen_input_file':None}
DEFAULTS = {
    'evaluate_astra':                _get_defaults(run_astra, EXTRA ),
    'evaluate_astra_with_generator': _get_defaults(run_astra_with_generator, EXTRA) ,
    'evaluate_astra_with_distgen':   _get_defaults(run_astra, EXTRA2)
}


def evaluate_astra(settings, archive_path=None, merit_f=None, **params):
    """
    Convenience wrapper. See evaluate. 
    """
    return evaluate(settings, simulation='astra', 
                    archive_path=archive_path, merit_f=merit_f, **params)


def evaluate_astra_with_generator(settings, archive_path=None, merit_f=None, **params):
    """
    Convenience wrapper. See evaluate. 
    """
    return evaluate(settings, simulation='astra_with_generator', 
                    archive_path=archive_path, merit_f=merit_f, **params)

def evaluate_astra_with_distgen(settings, archive_path=None, merit_f=None, **params):
    """
    Convenience wrapper. See evaluate. 
    """
    return evaluate(settings, simulation='astra_with_distgen', 
                    archive_path=archive_path, merit_f=merit_f, **params)


#-------------
# Return evaluate and its options. 

def configure_astra_evaluate(simulation='astra', config={}):
    """
    Returns a dict:
        'evaluate_f' : function that evaluates the simulation with one positional argument, and options. 
                       settings, **options
        'options'    : The optional arguments for that function, configured with config and templates. 
    
    
    Example:
        configure_astra_evaluate('astra', {'astra_input_file':'astra.in'})
    
    """

    
    # opts will become the new config
    opts = {'simulation':simulation}
    # Get defaults
    opts.update(DEFAULTS['evaluate_'+simulation])
    for k, v in config.items():
        if k in opts:
            opts[k] = v
        else:
            print(f'Uknown option for {simulation}:{k}:{v}')
            raise
    
    return {'evaluate_f':evaluate, 'options': opts}
