# -*- encoding:utf-8 -*-

import sys
import argparse
import itertools
import multiprocessing
import asyncio
import time

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

##################################################
#                初期処理関連                 
##################################################
is_running_process = True         # TODO: remove
is_output_suspend = False         # TODO: remove

NORMAL_EXIT = 0
ERROR_EXIT = 1

OUTPUT_IMAGE_DIR = "output/Image"
OUTPUT_FIGURE_DIR = "output/Figure"
COLORS = {
  "blue": "b",
  "green": "g",
  "red": "r",
  "cyan": "c",
  "magenta": "m",
  "yellow": "y",
  "black": "k",
  "white": "w"
}
DEFAULT_EQUAL_WIDTH_BINS = 255
WHITE_PADDING = "                                                "

WINDOW_TITLE_PREFIX = "Figure of "
WINDOW_TITLE_SUFFIX = " - Normalized"

DEFAULT_FIGURE_TITLE_NAME = "Figure" + WINDOW_TITLE_SUFFIX
HUE_FIGURE_TITLE_NAME = WINDOW_TITLE_PREFIX + "Hue" + WINDOW_TITLE_SUFFIX
SATURATION_FIGURE_TITLE_NAME = WINDOW_TITLE_PREFIX + "Saturation" + WINDOW_TITLE_SUFFIX
BRIGHTNESS_FIGURE_TITLE_NAME = WINDOW_TITLE_PREFIX + "Brightness" + WINDOW_TITLE_SUFFIX

input_file_name = ""
output_file_name = ""
prefix_figure_title_name = ""
equal_width = DEFAULT_EQUAL_WIDTH_BINS 
is_dny_output = False
verbosity = 0

NOMAL_MODE = 0
NOISY_MODE = 1
VERY_NOISY_MODE = 2

MAIN_PROCESS_IS_IN_PROGRESS = "InProgress"
MAIN_PROCESS_WAS_FINISHED = "Finish"
MAIN_PROCESS_REQUESTS_SLEEP_CALL = "Wait" 

sync_queue = multiprocessing.Queue()

##################################################
#              デバッグ情報表示用                 
##################################################
def PrintDebugInfomation(input_image, hsv_image, hue_image, saturation_image, brightness_image):
  print("\r", input_image.format, input_image.size, input_image.mode)
  print(hsv_image.format, hsv_image.size, hsv_image.mode)
  print("hue object: ", hue_image)
  print("saturation object: ", saturation_image)
  print("brightness object: ", brightness_image)

##################################################
#         実行中のアニメーション表示用                 
##################################################
def WaitngAnimate(sync_queue):
  animation_dot = ['       ', '.      ', '..     ', '...    ', '....   ', '...... ']
  dot_idx = 0
  dot_len = len(animation_dot) - 1
  main_process_state = MAIN_PROCESS_IS_IN_PROGRESS
  
  try:
    for animation_cycle in itertools.cycle(['|', '/', '-', '\\']):
      if sync_queue.qsize() > 0:
        if sync_queue.get() == MAIN_PROCESS_WAS_FINISHED:
          break
        elif sync_queue.get() == MAIN_PROCESS_REQUESTS_SLEEP_CALL:
          main_process_state = MAIN_PROCESS_REQUESTS_SLEEP_CALL
        elif sync_queue.get() == MAIN_PROCESS_IS_IN_PROGRESS:
          main_process_state = MAIN_PROCESS_IS_IN_PROGRESS
      if main_process_state == MAIN_PROCESS_REQUESTS_SLEEP_CALL:
        time.sleep(0.1)
        continue
      sys.stdout.write('\r['+ animation_cycle + ']: Image analyzer is now in progress' + animation_dot[dot_idx])
      if dot_idx == dot_len:
        dot_idx = 0
      else:
        dot_idx += 1
      time.sleep(0.1)
    sys.stdout.write('\r[*]: Done!                                                 \n')
  except Exception as e:
    print("Unexpected error: " + str(e))
    sys.exit(ERROR_EXIT)
  except KeyboardInterrupt:
    pass
  
  sys.exit(NORMAL_EXIT)

##################################################
#                  引数制御用                
##################################################
def DefineSystemArgumentsProcess():
  global input_file_name
  global output_file_name
  global prefix_figure_title_name
  global equal_width
  global is_dny_output
  global verbosity
  
  parser = argparse.ArgumentParser(description="Create a separated HSV parameter image and making these figures.")
  parser._action_groups.pop()
  required = parser.add_argument_group('required arguments')
  optional = parser.add_argument_group('optional arguments')
  optional.add_argument("-v", "--verbosity", default=0, action="count", help="Increase output verbosity. The value is up to 2.")
  optional.add_argument("-e", "--equal-width", type=int, default=DEFAULT_EQUAL_WIDTH_BINS, help="Set histogram figures's equal-width bins. The default value is 255.")
  optional.add_argument("-o", "--output-file", "--output-file-prefix", type=str, default="", help="The prefix result file name.")
  optional.add_argument("-d", "--is-dny-output", action='store_const', default=False, const=True, help="Deny output to the HSV files.")
  required.add_argument("-f", "--file", type=str, help="The analyzer target file name.", required=True)
  args = parser.parse_args()
  
  input_file_name = args.file
  if args.output_file != "":
    output_file_name = args.output_file + "_"
    prefix_figure_title_name = '[ ' + args.output_file + ' ]: '
  equal_width = args.equal_width
  is_dny_output = args.is_dny_output
  verbosity = args.verbosity 
  
  if verbosity == VERY_NOISY_MODE:
    print(args)

##################################################
#                  グラフ制御用                 
##################################################
def MakePlotFigure(hsv_base_image: Image, figure, plot_color: str, 
                   figure_title: str, xlabel: str, ylabel: str, equal_width_bins: int,
                   output_prefix_name: str, output_suffix_name: str):
  global is_output_suspend      # TODO: remove
  global is_dny_output
  
  figure_base_data=list(hsv_base_image.getdata())
  if verbosity == VERY_NOISY_MODE:
    sync_queue.put(MAIN_PROCESS_REQUESTS_SLEEP_CALL)
    time.sleep(0.5)
    print("\r>", output_suffix_name, WHITE_PADDING)
    print("\r   MAX:", max(figure_base_data), " , min: ", min(figure_base_data), WHITE_PADDING)
    sync_queue.put(MAIN_PROCESS_IS_IN_PROGRESS)
  figure.hist(figure_base_data, bins=equal_width_bins, density=True, color=plot_color)
  figure.set_title(figure_title)
  figure.set_xlabel(xlabel)
  figure.set_ylabel(ylabel)
  if verbosity == NOISY_MODE or verbosity == VERY_NOISY_MODE:
    hsv_base_image.show()
  if is_dny_output == False:
    with open(OUTPUT_IMAGE_DIR  + "/" + output_prefix_name + output_suffix_name, "wb") as pointer_of_output_image_file:
      hsv_base_image.save(pointer_of_output_image_file, 'PNG')

##################################################
#                   主処理                 
##################################################
def AnalyzeImage():
  global is_running_process     # TODO: remove
  global input_file_name
  global prefix_figure_title_name
  
  hue_figure_title_name_with_prefix = prefix_figure_title_name + HUE_FIGURE_TITLE_NAME
  saturation_figure_title_name_with_prefix = prefix_figure_title_name + SATURATION_FIGURE_TITLE_NAME
  brightness_figure_title_name_with_prefix = prefix_figure_title_name + BRIGHTNESS_FIGURE_TITLE_NAME
  
  try:
    wait_controller = multiprocessing.Process(target=WaitngAnimate, args=(sync_queue,))
    wait_controller.start()
    
    with open(input_file_name, "rb") as pointer_of_input_image:
      input_image = Image.open(pointer_of_input_image)
    
      hsv_image = input_image.convert("HSV")
      hue_image, saturation_image, brightness_image = input_image.convert("HSV").split()
      
      if verbosity >= VERY_NOISY_MODE:
        PrintDebugInfomation(input_image, hsv_image, hue_image, saturation_image, brightness_image)
      
      figure_hue = plt.figure(hue_figure_title_name_with_prefix)
      figure_saturation = plt.figure(saturation_figure_title_name_with_prefix)
      figure_brightness = plt.figure(brightness_figure_title_name_with_prefix)
      hue_plot = figure_hue.add_subplot(1,1,1)
      saturation_plot = figure_saturation.add_subplot(1,1,1)
      brightness_plot = figure_brightness.add_subplot(1,1,1)
      
      MakePlotFigure(hsv_base_image = hue_image,
                    figure = hue_plot,
                    plot_color = COLORS["blue"],
                    figure_title = hue_figure_title_name_with_prefix,
                    xlabel = 'Value of Hue', ylabel = 'Frequent',
                    equal_width_bins = equal_width,
                    output_prefix_name = output_file_name,
                    output_suffix_name = 'Image_Hue.png')
      
      MakePlotFigure(hsv_base_image = saturation_image,
                    figure = saturation_plot,
                    plot_color = COLORS["blue"],
                    figure_title = saturation_figure_title_name_with_prefix,
                    xlabel = 'Value of Saturation', ylabel = 'Frequent',
                    equal_width_bins = equal_width,
                    output_prefix_name = output_file_name,
                    output_suffix_name = 'Image_Saturation.png')
                    
      MakePlotFigure(hsv_base_image = brightness_image,
                    figure = brightness_plot,
                    plot_color = COLORS["blue"],
                    figure_title = brightness_figure_title_name_with_prefix,
                    xlabel = 'Value of Brightness', ylabel = 'Frequent',
                    equal_width_bins = equal_width,
                    output_prefix_name = output_file_name,
                    output_suffix_name = 'Image_Brightness.png')
      
      figure_hue.savefig(OUTPUT_FIGURE_DIR + "/" + output_file_name + 'Image_Hue.png')
      figure_saturation.savefig(OUTPUT_FIGURE_DIR + "/" + output_file_name + 'Image_Saturation.png')
      figure_brightness.savefig(OUTPUT_FIGURE_DIR + "/" + output_file_name + 'Image_Brightness.png')
      
      sync_queue.put(MAIN_PROCESS_WAS_FINISHED)
      plt.show()
      
  except Exception as e:
    wait_controller.terminate()
    print("Unexpected error: " + str(e)) 
    sys.exit(ERROR_EXIT)
  except KeyboardInterrupt:
    wait_controller.terminate()
  
  return NORMAL_EXIT

##################################################
#                    Main                 
##################################################
if __name__ == '__main__':
  try:
    DefineSystemArgumentsProcess()
    AnalyzeImage()
  except Exception as e:
    print("Unexpected error: " + str(e)) 
    sys.exit(ERROR_EXIT)
  
  sys.exit(NORMAL_EXIT)
