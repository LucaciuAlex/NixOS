from pathlib import Path
import subprocess
import shlex



class Tools:

    # Define as singleton
    _instance = None
    def __new__(self, *argc, **argv):
        if self._instance is None:
            # Create one instance the first time it is called()
            self._instance = super().__new__(self, *argc, **argv)
            self._instance._initialized = False
        return self._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.ALLOWED_ROOT = Path.cwd()
        self.INTERNAL_GIT = ".internal_git"
        self.INTERNAL_GITIGNORE = ".internal_gitignore"
        self.internal_git = ["git",f"--git-dir={self.INTERNAL_GIT}", "-c", f"core.excludesFile={self.INTERNAL_GITIGNORE}"]
        # git --git-dir=.internal_git -c core.excludesFile=.internal_gitignore

        # internal state
        self.retrigger = False
        self.nextReasoningStep = ""

        # commands
        self.git = self.Git(self._instance)


    ###
    ###
    ###
    def continueRound(self, arguments=""):
        thinking = str(arguments.get("retrigger"))

        base_msg = (
            "The tool execution has completed and the output is provided above. "
            "Do not stop. Immediately continue executing the user's original task based on this new data. "
        )

        if thinking == "-1":
            return 
        if thinking == "0":
            self.retrigger = True
            self.nextReasoningStep = base_msg + "Continue round. Thinking budget for this turn: no_thinking."
            print(f"thinking 0, should retrigger: {self.retrigger}")

        if thinking == "1":
            self.retrigger = True
            self.nextReasoningStep = base_msg + "Continue round. Thinking budget for this turn: minimal."
            print(f"thinking 1, should retrigger: {self.retrigger}")

        if thinking == "2":
            self.retrigger = True
            self.nextReasoningStep = base_msg + "Continue round. Thinking budget for this turn: normal."
            print(f"thinking 2, should retrigger: {self.retrigger}")

    def shouldContinue(self):
        print(f"retrigger value: {self.retrigger}")

        retrigger = self.retrigger
        self.retrigger = False

        print(f"returned value: {retrigger}")

        return retrigger

    def shouldThink(self):
        thinking = self.nextReasoningStep
        self.nextReasoningStep = ""

        return thinking

    ###
    ### create_file function. Used to create files in the current filesystem. 
    ###
    def create_file(self, arguments=""):
        file_path = arguments.get("file_path")
        content = arguments.get("content")
        if "encoding" in arguments.keys():
            encoding = arguments.get("encoding") 
        else:
            encoding="utf-8"

        self.continueRound(arguments)
        
        # Security sandbox check
        full_path = (self.ALLOWED_ROOT / file_path).resolve()
        if not str(full_path).startswith(str(self.ALLOWED_ROOT.resolve())):
            return "Error: Permission denied. Path is outside the allowed root directory."
        
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding=encoding) as f:
                f.write(content)
            return f"Success: File created at {full_path}"
        except Exception as e:
            return f"Error writing file: {e}"

    ###
    ### read_file function. Used to read files from within the current filesystem. 
    ###
    def read_file(self, arguments=""):
        file_path = arguments.get("file_path")

        self.continueRound(arguments)

        # Security sandbox check
        full_path = (self.ALLOWED_ROOT / file_path).resolve()
        if not str(full_path).startswith(str(self.ALLOWED_ROOT.resolve())):
            return "Error: Permission denied. Path is outside the allowed root directory."
        
        try:
            with open(full_path, "r") as f:
                return f.read()
        except Exception as e:
            return f"Error opening {file_path}: {e}"
    

    ###
    ### Git commands used to save and revert the changes done by the agent. The changes are saved in the file {.internal_git}
    ###
    class Git:

        # Define as singleton
        _instance = None
        def __new__(self, *argc, **argv):
            if self._instance is None:
                # Create one instance the first time it is called()
                self._instance = super().__new__(self)
            return self._instance
            
        def __init__(self, outer_instance):
            self.outer = outer_instance 


        ###
        ### Git status function used to retrieve the status of the internal git branch 
        ###
        def status(self, arguments=""):
            params = shlex.split(arguments.get("parameters"))

            self.outer.continueRound(arguments)

            gitStatusProcess = subprocess.Popen( self.outer.internal_git + ["status"] + params, stdout=subprocess.PIPE, text=True)
            return gitStatusProcess.communicate()[0]

        ###
        ### Git add function used to stage specific files to the internal git
        ###
        def add(self, arguments=""):
            params = shlex.split(arguments.get("parameters"))

            self.outer.continueRound(arguments)

            gitAddProcess = subprocess.Popen( self.outer.internal_git + ["add"] + params, stdout=subprocess.PIPE, text=True)
            return gitAddProcess.communicate()[0]

        ###
        ### Git reset function used to unstage specific files from the internal git
        ###
        def reset(self, arguments=""):
            params = shlex.split(arguments.get("parameters"))

            self.outer.continueRound(arguments)

            gitStatusProcess = subprocess.Popen( self.outer.internal_git + ["reset"] + params, stdout=subprocess.PIPE, text=True)
            return gitStatusProcess.communicate()[0]
        
        ###
        ### Git commit function used to commit stages changes to the internal git branch 
        ###
        def commit(self, arguments=""):
            params = shlex.split(arguments.get("parameters"))

            self.outer.continueRound(arguments)

            gitStatusProcess = subprocess.Popen( self.outer.internal_git + ["commit"] + params, stdout=subprocess.PIPE, text=True)
            return gitStatusProcess.communicate()[0]

        ###
        ### Git checkout function used to commit stages changes to the internal git branch 
        ###
        def checkout(self, arguments=""):
            params = shlex.split(arguments.get("parameters"))

            self.outer.continueRound(arguments)

            gitStatusProcess = subprocess.Popen( self.outer.internal_git + ["checkout"] + params, stdout=subprocess.PIPE, text=True)
            return gitStatusProcess.communicate()[0]



