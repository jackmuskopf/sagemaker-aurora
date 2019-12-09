import subprocess

def run_cmd(*args, **kwargs):
    """
    #########################################################################
    ############## Wrapper for subprocess - run shell commands ##############
    #########################################################################
    Will run the bash command defined by *args
    i.e.,   self.run_cmd("echo", "hi") -> echo hi
            self.run_cmd("docker", "run", "-it", "--env-file=.env", "some_image") -> docker run -it --env-file=.env some_image
    """
    cmd_string = ' '.join(args)


    popen_kwargs = dict(
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        )

    popen_addtional_kwargs = ['WorkingDirectory', 'ShellEnvironment']

    for kw in popen_addtional_kwargs:
        if kwargs.get(kw):
            popen_kwargs[kw] = kwargs.get(kw)
    
    
    proc = subprocess.Popen(args, **popen_kwargs)
    
    stdout, stderr = proc.communicate()
    stdout = stdout.decode("utf-8")
    stderr = stderr.decode("utf-8")
    
    return {
        'stdout' : stdout,
        'stderr' : stderr,
        'exit_code' : proc.returncode
    }