from base.application import create_app

# Attach Debugger
'''
try:
  import googleclouddebugger
  googleclouddebugger.enable(
      breakpoint_enable_canary=True,
      service_account_json_file='env_config/client-secret.json')
except ImportError:
  pass
'''

# Initialize application
app = create_app()