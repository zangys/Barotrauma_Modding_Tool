import gc
import logging
import queue
import threading
import dearpygui.dearpygui as dpg

from Code.handlers import ModManager


class App:
    ui_tasks_queue: queue.Queue = queue.Queue()

    @staticmethod
    def run() -> None:
        try:
            while dpg.is_dearpygui_running():
                while not App.ui_tasks_queue.empty():
                    try:
                        task = App.ui_tasks_queue.get_nowait()
                        task()
                    except Exception as e:
                        logging.error(f"Error in UI task: {e}")
                dpg.render_dearpygui_frame()

        except Exception as e:
            logging.error(f"Error during running GUI: {e}")

        finally:
            logging.debug("Destroying app...")

            active_threads = [
                t
                for t in threading.enumerate()
                if not t.daemon and t != threading.current_thread()
            ]
            for thread in active_threads:
                logging.debug(f"Waiting for thread to finish: {thread.name}")
                thread.join(timeout=2.0)

            try:
                ModManager.save_mods()
            except Exception as e:
                logging.error(f"Error saving mods during shutdown: {e}")

            gc.collect()
            logging.debug("Starting final cleanup...")

            for thread in threading.enumerate():
                logging.debug(
                    f"Thread Name: {thread.name}, Alive: {thread.is_alive()}, Daemon: {thread.daemon}"
                )

            try:
                dpg.stop_dearpygui()
                dpg.destroy_context()
                logging.debug("DPG context destroyed successfully")
            except Exception as e:
                logging.error(f"Error destroying DPG context: {e}")

    @staticmethod
    def stop() -> None:
        logging.debug("Stopping application...")
        dpg.stop_dearpygui()
