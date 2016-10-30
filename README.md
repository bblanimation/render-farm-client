# RenderFarm README

Scripts and associated files for rendering Blender frames on the CSE remote servers (Blender version: 2.77)


Client-side improvements for future implementation:
* Open last used file to main menu automatically

* Integrate render.py with sendSpecificFiles.py

* Notify when a frame has been rendered

* Use ssh redirect in 'render.py' so that I can render remotely

* Add user input for samples and size %


Server-side improvements for future implementation:
* Add elapsed time to 'render completed successfully!' message

* Give user some sort of status for the render (e.g. 5% done)

* Add user input for samples and size %

* Notify user when an individual file has been rendered

* Sync files one by one (in case of host failure)

* Fix unknown host failures bugs found when running overnight

* Optimize default render settings

* Re-render failed frames automatically
