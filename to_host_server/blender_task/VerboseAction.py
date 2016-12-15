import argparse

# Thanks to: http://stackoverflow.com/questions/6076690/verbose-level-with-argparse-and-multiple-v-options
class verbose_action(argparse.Action):
    def __call__(self,parser,args,values,options_string=None):
        if(values==None):
            values='1'
        try:
            values = int(values)
        except ValueError:
            values = values.count('v')+1
        setattr(args,self.dest,values)
