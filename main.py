# -*- encoding:utf-8 -*-

import os
import sys
import re
import argparse
import itertools
import multiprocessing
import asyncio
import time
import glob

import numpy as np
import matplotlib.pyplot as plt
import japanize_matplotlib
from PIL import Image

##################################################
#                初期処理関連                 
##################################################
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
DEFAULT_NUMBER_OUTPUT_FORMAT='{:.1f}'
WHITE_PADDING = "                                                "

# グラフタイトル用の変数
ENGLISH_WINDOW_TITLE_PREFIX = "Figure of "
ENGLISH_WINDOW_TITLE_SUFFIX = " - Normalized"
ENGLISH_DEFAULT_FIGURE_TITLE_NAME = "Figure" + ENGLISH_WINDOW_TITLE_SUFFIX
JAPANESE_WINDOW_TITLE_PREFIX = "図表: "
JAPANESE_WINDOW_TITLE_SUFFIX = " - 正規化済み"
JAPANESE_DEFAULT_FIGURE_TITLE_NAME = "図表: " + JAPANESE_WINDOW_TITLE_SUFFIX
HUE_FIGURE_TITLE_NAME = {
  'english': ENGLISH_WINDOW_TITLE_PREFIX + "Hue" + ENGLISH_WINDOW_TITLE_SUFFIX,
  'japanese': JAPANESE_WINDOW_TITLE_PREFIX + "色相" + JAPANESE_WINDOW_TITLE_SUFFIX
}
SATURATION_FIGURE_TITLE_NAME = {
  'english': ENGLISH_WINDOW_TITLE_PREFIX + "Saturation" + ENGLISH_WINDOW_TITLE_SUFFIX,
  'japanese': JAPANESE_WINDOW_TITLE_PREFIX + "彩度" + JAPANESE_WINDOW_TITLE_SUFFIX
}
BRIGHTNESS_FIGURE_TITLE_NAME = {
  'english': ENGLISH_WINDOW_TITLE_PREFIX + "Brightness" + ENGLISH_WINDOW_TITLE_SUFFIX,
  'japanese': JAPANESE_WINDOW_TITLE_PREFIX + "明度" + JAPANESE_WINDOW_TITLE_SUFFIX
}

input_file_name = ""
output_file_name = ""
prefix_figure_title_name = ""
equal_width = DEFAULT_EQUAL_WIDTH_BINS 
is_dny_output = False
use_interactive_mode = False
verbosity = 0
default_xlim_max = 255
default_xlim_min = 0
regex_file_name_pattern = r'.+\.(png|PNG|jpg|jpeg|JPG|JPEG)'

DEFAULT_X_TEXT_POSITON = 5
DEFAULT_Y_TEXT_POSITON = 0
DEFAULT_BACKGROUND_COLOR = "#ffffff"

NOMAL_MODE = 0
NOISY_MODE = 1
VERY_NOISY_MODE = 2

MAIN_PROCESS_IS_IN_PROGRESS = "InProgress"
MAIN_PROCESS_WAS_FINISHED = "Finish"
MAIN_PROCESS_REQUESTS_SLEEP_CALL = "Wait" 

sync_queue = multiprocessing.Queue(16)

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
def WaitingAnimate(sync_queue):
  global NOMAL_MODE
  global NOISY_MODE
  global VERY_NOISY_MODE

  global MAIN_PROCESS_IS_IN_PROGRESS
  global MAIN_PROCESS_WAS_FINISHED
  global MAIN_PROCESS_REQUESTS_SLEEP_CALL
  
  animation_dot = ['       ', '.      ', '..     ', '...    ', '....   ', '...... ']
  dot_idx = 0
  dot_len = len(animation_dot) - 1
  main_process_state = MAIN_PROCESS_IS_IN_PROGRESS
  queue_value = ""
  
  try:
    for animation_cycle in itertools.cycle(['|', '/', '-', '\\']):
      if sync_queue.empty() == False:
        queue_value = sync_queue.get() 
        if queue_value == MAIN_PROCESS_WAS_FINISHED:
          break
        elif queue_value == MAIN_PROCESS_REQUESTS_SLEEP_CALL:
          main_process_state = MAIN_PROCESS_REQUESTS_SLEEP_CALL
        elif queue_value == MAIN_PROCESS_IS_IN_PROGRESS:
          main_process_state = MAIN_PROCESS_IS_IN_PROGRESS
      if main_process_state == MAIN_PROCESS_REQUESTS_SLEEP_CALL:
        pass
      else:
        sys.stdout.write('\r['+ animation_cycle + ']: Image analyzer is now in progress' + animation_dot[dot_idx])
        if dot_idx == dot_len:
          dot_idx = 0
        else:
          dot_idx += 1
      time.sleep(0.1)
    sys.stdout.write('\r[+]: Done🎉                                                 \n')
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
  global use_interactive_mode
  global verbosity
  
  try:
    parser = argparse.ArgumentParser(description="Create a separated HSV parameter image and making these figures.")
    parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')
    optional.add_argument("-v", "--verbosity", default=0, action="count", help="Increase output verbosity. The value is up to 2.")
    optional.add_argument("-e", "--equal-width", type=int, default=DEFAULT_EQUAL_WIDTH_BINS, help="Set histogram figures's equal-width bins. The default value is 255.")
    optional.add_argument("-o", "--output-file", "--output-file-prefix", type=str, default="", help="The prefix result file name.If batch mode, this parameter will ignore.")
    optional.add_argument("-d", "--is-dny-output", action='store_const', default=False, const=True, help="Deny output to the HSV files.")
    optional.add_argument("-i", "--use-interactive-mode", action='store_const', default=False, const=True, help="Use interactive mode.")
    optional.add_argument("-f", "--file", type=str, default="", help="The analyzer target file name.")
    args = parser.parse_args()
    
    input_file_name = args.file
    if args.output_file != "":
      output_file_name = args.output_file + "_"
      prefix_figure_title_name = '【 ' + args.output_file + ' 】 '
    equal_width = args.equal_width
    is_dny_output = args.is_dny_output
    use_interactive_mode = args.use_interactive_mode
    verbosity = args.verbosity 
    
    if verbosity == VERY_NOISY_MODE:
      print(args)
  except Exception as e:
    print("\nUnexpected error: " + str(e)) 
    sys.exit(ERROR_EXIT)
  except KeyboardInterrupt:
    print("\nKeyboard Interrupt: The script aborted.")
    sys.exit(NORMAL_EXIT)
  
  return NORMAL_EXIT

##################################################
#                  算術換算用                 
##################################################
def CalcMeanValues(hue_data: np.array, saturation_data: np.array, brightness_data: np.array):
  global DEFAULT_NUMBER_OUTPUT_FORMAT
  
  return np.float64(DEFAULT_NUMBER_OUTPUT_FORMAT.format(np.mean(hue_data, dtype=np.float64))), \
            np.float64(DEFAULT_NUMBER_OUTPUT_FORMAT.format(np.mean(saturation_data, dtype=np.float64))), \
              np.float64(DEFAULT_NUMBER_OUTPUT_FORMAT.format(np.mean(brightness_data, dtype=np.float64)))
              
def CalcMedianValues(hue_data: np.array, saturation_data: np.array, brightness_data: np.array):
  global DEFAULT_NUMBER_OUTPUT_FORMAT
  
  return np.float64(DEFAULT_NUMBER_OUTPUT_FORMAT.format(np.median(hue_data))), \
            np.float64(DEFAULT_NUMBER_OUTPUT_FORMAT.format(np.median(saturation_data))), \
              np.float64(DEFAULT_NUMBER_OUTPUT_FORMAT.format(np.median(brightness_data)))

##################################################
#                  グラフ制御用                 
##################################################
def MakePlotFigure(hsv_base_image: Image, figure, plot_color: str, 
                   figure_title: str, xlabel: str, ylabel: str, equal_width_bins: int,
                   output_prefix_name: str, output_suffix_name: str):
  global sync_queue
  
  global NOMAL_MODE
  global NOISY_MODE
  global VERY_NOISY_MODE

  global MAIN_PROCESS_IS_IN_PROGRESS
  global MAIN_PROCESS_WAS_FINISHED
  global MAIN_PROCESS_REQUESTS_SLEEP_CALL
                   
  global is_dny_output
  
  figure_base_data=list(hsv_base_image.getdata())
  if verbosity == VERY_NOISY_MODE:
    sync_queue.put_nowait(MAIN_PROCESS_REQUESTS_SLEEP_CALL)
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
def AnalyzeImage(process_file_name: str, batch_mode: bool):
  global sync_queue
  
  global NOMAL_MODE
  global NOISY_MODE
  global VERY_NOISY_MODE

  global MAIN_PROCESS_IS_IN_PROGRESS
  global MAIN_PROCESS_WAS_FINISHED
  global MAIN_PROCESS_REQUESTS_SLEEP_CALL
  
  global input_file_name
  global output_file_name
  global prefix_figure_title_name
  global use_interactive_mode
  
  global default_xlim_max
  global default_xlim_min
  
  # グラフ表示の制御用変数
  hue_figure_title_name_with_prefix = prefix_figure_title_name + HUE_FIGURE_TITLE_NAME['japanese']
  saturation_figure_title_name_with_prefix = prefix_figure_title_name + SATURATION_FIGURE_TITLE_NAME['japanese']
  brightness_figure_title_name_with_prefix = prefix_figure_title_name + BRIGHTNESS_FIGURE_TITLE_NAME['japanese']
  xlabel_list = {
    'hue_label': {
      'english': 'Value of Hue',
      'japanese': '色相の値'
    },
    'saturation_label': {
      'english': 'Value of saturation',
      'japanese': '彩度の値'
    },
    'brightness_label': {
      'english': 'Value of brightness',
      'japanese': '明度の値'
    },
  }
  ylabel_list = {
    'hue_label': {
      'english': 'Frequent',
      'japanese': '頻出度'
    },
    'saturation_label': {
      'english': 'Frequent',
      'japanese': '頻出度'
    },
    'brightness_label': {
      'english': 'Frequent',
      'japanese': '頻出度'
    },
  }
  mean_label = {
    'english': 'Mean',
    'japanese': '平均値'
  }
  median_label = {
    'english': 'Median',
    'japanese': '中央値'
  }
  
  try:
    wait_controller = multiprocessing.Process(target=WaitingAnimate, args=(sync_queue,))
    wait_controller.start()

    if batch_mode == True:
      input_file_name = process_file_name
      base_file_name = os.path.basename(process_file_name).split('.')[0]
      output_file_name = base_file_name + "_"
      prefix_figure_title_name = ""
      suffix_figure_title_name = " - " + base_file_name
      
      # グラフのタイトルをファイル名から動的に付与
      hue_figure_title_name_with_prefix = HUE_FIGURE_TITLE_NAME['japanese'] + suffix_figure_title_name
      saturation_figure_title_name_with_prefix = SATURATION_FIGURE_TITLE_NAME['japanese'] + suffix_figure_title_name
      brightness_figure_title_name_with_prefix = BRIGHTNESS_FIGURE_TITLE_NAME['japanese'] + suffix_figure_title_name
    else:
      pass
      
    with open(input_file_name, "rb") as pointer_of_input_image:
      input_image = Image.open(pointer_of_input_image)
    
      hsv_image = input_image.convert("HSV")
      hue_image, saturation_image, brightness_image = input_image.convert("HSV").split()
      
      if verbosity >= VERY_NOISY_MODE:
        PrintDebugInfomation(input_image, hsv_image, hue_image, saturation_image, brightness_image)
      
      hue_data = np.array(list(hue_image.getdata()))
      saturation_data = np.array(list(saturation_image.getdata()))
      brightness_data = np.array(list(brightness_image.getdata()))
      
      hue_mean, saturation_mean, brightness_mean = CalcMeanValues(hue_data, saturation_data, brightness_data)
      hue_median, saturation_median, brightness_median = CalcMedianValues(hue_data, saturation_data, brightness_data)
      
      if verbosity == VERY_NOISY_MODE:
        sync_queue.put_nowait(MAIN_PROCESS_REQUESTS_SLEEP_CALL)
        time.sleep(0.5)
        print("\rhue mean:", hue_mean, ", hue median :", hue_median, WHITE_PADDING)
        print("\rsaturation mean:", saturation_mean, ", saturation median :", saturation_median, WHITE_PADDING)
        print("\rbrightness mean:", brightness_mean, ", brightness median :", brightness_median, WHITE_PADDING)
        sync_queue.put(MAIN_PROCESS_IS_IN_PROGRESS)
      
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
                    xlabel = xlabel_list['hue_label']['japanese'], ylabel = ylabel_list['hue_label']['japanese'],
                    equal_width_bins = equal_width,
                    output_prefix_name = output_file_name,
                    output_suffix_name = 'Image_Hue.png')
      
      MakePlotFigure(hsv_base_image = saturation_image,
                    figure = saturation_plot,
                    plot_color = COLORS["blue"],
                    figure_title = saturation_figure_title_name_with_prefix,
                    xlabel = xlabel_list['saturation_label']['japanese'], ylabel = ylabel_list['saturation_label']['japanese'],
                    equal_width_bins = equal_width,
                    output_prefix_name = output_file_name,
                    output_suffix_name = 'Image_Saturation.png')
                    
      MakePlotFigure(hsv_base_image = brightness_image,
                    figure = brightness_plot,
                    plot_color = COLORS["blue"],
                    figure_title = brightness_figure_title_name_with_prefix,
                    xlabel = xlabel_list['brightness_label']['japanese'], ylabel = ylabel_list['brightness_label']['japanese'],
                    equal_width_bins = equal_width,
                    output_prefix_name = output_file_name,
                    output_suffix_name = 'Image_Brightness.png')
                    
      hue_plot.set_xlim(left=default_xlim_min, right=default_xlim_max)
      saturation_plot.set_xlim(left=default_xlim_min, right=default_xlim_max)
      brightness_plot.set_xlim(left=default_xlim_min, right=default_xlim_max)
      
      y_bottom = 0.0
      y_top = 0.0
      y_position = 0.0
      template_phrase_show_analytics_values = '{:>7}: {:>4.1f}\n{:>7}: {:>4.1f}'
      
      y_bottom, y_top = hue_plot.get_ylim()
      y_position = y_top * 0.98                   # 係数は暫定
      hue_plot.text(DEFAULT_X_TEXT_POSITON, y_position, template_phrase_show_analytics_values.format(mean_label['japanese'], hue_mean, median_label['japanese'], hue_median), \
                        fontsize=8,verticalalignment="top", backgroundcolor=DEFAULT_BACKGROUND_COLOR)
      y_bottom, y_top = saturation_plot.get_ylim()
      y_position = y_top * 0.98                   # 係数は暫定
      saturation_plot.text(DEFAULT_X_TEXT_POSITON, y_position, template_phrase_show_analytics_values.format(mean_label['japanese'], saturation_mean, median_label['japanese'], saturation_median), \
                        fontsize=8,verticalalignment="top", backgroundcolor=DEFAULT_BACKGROUND_COLOR)
      y_bottom, y_top = brightness_plot.get_ylim()
      y_position = y_top * 0.98                   # 係数は暫定
      brightness_plot.text(DEFAULT_X_TEXT_POSITON, y_position, template_phrase_show_analytics_values.format(mean_label['japanese'], brightness_mean, median_label['japanese'], brightness_median), \
                        fontsize=8,verticalalignment="top", backgroundcolor=DEFAULT_BACKGROUND_COLOR)
      
      figure_hue.savefig(OUTPUT_FIGURE_DIR + "/" + output_file_name + 'Image_Hue.png')
      figure_saturation.savefig(OUTPUT_FIGURE_DIR + "/" + output_file_name + 'Image_Saturation.png')
      figure_brightness.savefig(OUTPUT_FIGURE_DIR + "/" + output_file_name + 'Image_Brightness.png')
      
      sync_queue.put(MAIN_PROCESS_WAS_FINISHED)
      time.sleep(0.5)
      if wait_controller.is_alive() == True:
        wait_controller.kill()
      
      if use_interactive_mode == True:
        plt.show()
        
      # 後処理(メモリ・リーク対策)
      plt.clf()
      plt.close(figure_hue)
      plt.close(figure_saturation)
      plt.close(figure_brightness)
      
  except Exception as e:
    wait_controller.terminate()
    print("\nUnexpected error: " + str(e)) 
    sys.exit(ERROR_EXIT)
  except KeyboardInterrupt:
    wait_controller.terminate()
    print("\nKeyboard Interrupt: The script aborted.")
    sys.exit(NORMAL_EXIT)
  
  return NORMAL_EXIT

##################################################
#                    Main                 
##################################################
if __name__ == '__main__':
  try:
    DefineSystemArgumentsProcess()
    
    # Batch mode
    if input_file_name == "":
      print("Enter batch mode:")
      filter_pattern = re.compile(regex_file_name_pattern)
      
      for str_file_name in glob.iglob('input/**', recursive=True):
        if filter_pattern.search(str_file_name) != None:
          print(str_file_name)
          AnalyzeImage(str_file_name, True)
      print("The process has been completed🎉")
    # Single file process mode
    else:
      print("Enter single file process mode:")
      AnalyzeImage(input_file_name, False)
    
  except Exception as e:
    print("\nUnexpected error: " + str(e)) 
    sys.exit(ERROR_EXIT)
  except KeyboardInterrupt:
    print("\nKeyboard Interrupt: The script aborted.")
    sys.exit(NORMAL_EXIT)
  
  sys.exit(NORMAL_EXIT)
