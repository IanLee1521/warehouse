# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import multiprocessing

import click
import gunicorn.app.base

from warehouse.cli import warehouse


class Application(gunicorn.app.base.BaseApplication):

    def __init__(self, configurator, *args, options, **kwargs):
        self.options = options
        self.configurator = configurator

        super().__init__(*args, **kwargs)

    def load_config(self):
        config = {
            key: value for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        # We wait to load the WSGI app until here, otherwise we'll trigger the
        # configuration of Warehouse before Gunicorn forks the workers, which
        # will remove our ability to reload Warehouse.
        return self.configurator.make_wsgi_app()


@warehouse.command()
@click.option("-b", "--bind", metavar="ADDRESS", help="The socket to bind.")
@click.option(
    "--reload/--no-reload", "reload_",
    help="Restart workers when code changes."
)
@click.option(
    "--workers", "-w",
    type=click.IntRange(min=1),
    help="How many workers to spawn. [default: (2 * $num_cores) + 1]",
)
@click.pass_obj
def serve(config, bind, reload_, workers):
    """
    Serve Warehouse using gunicorn.
    """

    # Default options which can be overriden later.
    options = {
        # The gunicorn docs recommend (2 x $num_cores) + 1
        "workers": (2 * multiprocessing.cpu_count()) + 1,
    }

    # We want these values to override the values from the config file if
    # they've been given.
    cli_options = {"bind": bind, "reload": reload_, "workers": workers}
    options.update({k: v for k, v in cli_options.items() if v is not None})

    # This is a non optional "option", we always want our proc_name to be
    # warehouse.
    options["proc_name"] = "warehouse"

    # Actually run our WSGI application now.
    Application(config, options=options).run()
