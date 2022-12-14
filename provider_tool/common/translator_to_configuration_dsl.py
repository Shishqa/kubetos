import copy

import six
from toscaparser.tosca_template import ToscaTemplate

from provider_tool.providers.common.tosca_template import ProviderToscaTemplate
from provider_tool.common.tosca_reserved_keys import IMPORTS, DEFAULT_ARTIFACTS_DIRECTORY,\
    EXECUTOR, NAME, TOSCA_ELEMENTS_MAP_FILE, TOSCA_ELEMENTS_DEFINITION_FILE
from provider_tool.common import utils
from provider_tool.common.configuration import Configuration


import logging
import json, os, sys, yaml


REQUIRED_CONFIGURATION_PARAMS = (TOSCA_ELEMENTS_DEFINITION_FILE, DEFAULT_ARTIFACTS_DIRECTORY, TOSCA_ELEMENTS_MAP_FILE)


def translate(template_file, validate_only, provider, configuration_tool, cluster_name, is_delete=False,
              a_file=True, extra=None, log_level='info', host_ip_parameter='public_address',
              public_key_path='~/.ssh/id_rsa.pub', grpc_cotea_endpoint=None):
    """
    Main function, is called by different shells, i.e. bash, Ansible module, grpc
    :param template_file: filename of TOSCA template or TOSCA template data if a_file is False
    :param validate_only: boolean, if template should be only validated
    :param provider: key of cloud provider
    :param configuration_tool: key of configuration tool
    :param cluster_name: name to point to desired infrastructure as one component
    :param is_delete: generate dsl scripts for infrastructure deletion
    :param a_file: if template_file is filename
    :param extra: extra for template
    :return: string that is a script to deploy or delete infrastructure
    """
    log_map = dict(
        debug=logging.DEBUG,
        info=logging.INFO,
        warning=logging.WARNING,
        error=logging.ERROR,
        critical=logging.ERROR
    )

    logging_format = "%(asctime)s %(levelname)s %(message)s"
    logging.basicConfig(filename='.clouni-provider-tool.log', filemode='a', level=log_map[log_level],
                        format=logging_format, datefmt='%Y-%m-%d %H:%M:%S')
    logging.info("Started translation of TOSCA template \'%s\' for provider \'%s\' and configuration tool \'%s\'" %
                 (template_file if a_file else 'raw', provider, configuration_tool))
    logging.info("Cluster name set to \'%s\'" % cluster_name)
    logging.info("Deploying script for cluster %s will be created" % 'deletion' if is_delete else 'creation')
    logging.info("Extra parameters to the unit of deployment scripts will be added: %s" % json.dumps(extra))
    logging.info("Log level is set to %s" % log_level)

    config = Configuration()
    for sec in REQUIRED_CONFIGURATION_PARAMS:
        if sec not in config.get_section(config.MAIN_SECTION).keys():
            logging.error('Provider configuration parameter "%s" is missing in configuration file' % sec)
            raise Exception('Provider configuration parameter "%s" is missing in configuration file' % sec)

    if a_file:
        template_file = os.path.join(os.getcwd(), template_file)
        with open(template_file, 'r') as f:
            template_content = f.read()
    else:
        template_content = template_file

    try:
        template = yaml.load(template_content, Loader=yaml.SafeLoader)
    except yaml.scanner.ScannerError as e:
        logging.error("Error parsing TOSCA template: %s%s" % (e.problem, e.context_mark))
        raise Exception("Error parsing TOSCA template: %s%s" % (e.problem, e.context_mark))

    def_files = config.get_section(config.MAIN_SECTION).get(TOSCA_ELEMENTS_DEFINITION_FILE)
    if isinstance(def_files, six.string_types):
        def_files = [ def_files ]
    default_import_files = []
    for def_file in def_files:
        default_import_files.append(os.path.join(utils.get_project_root_path(), def_file))
    logging.info("Default TOSCA template definition file to be imported \'%s\'" % json.dumps(default_import_files))

    # Add default import of normative TOSCA types to the template
    template[IMPORTS] = template.get(IMPORTS, [])
    for i in range(len(template[IMPORTS])):
        if isinstance(template[IMPORTS][i], dict):
            for import_key, import_value in template[IMPORTS][i].items():
                if isinstance(import_value, six.string_types):
                    template[IMPORTS][i] = import_value
                elif isinstance(import_value, dict):
                    if import_value.get('file', None) is None:
                        logging.error("Imports %s doesn't contain \'file\' key" % import_key)
                        raise Exception("Imports %s doesn't contain \'file\' key" % import_key)
                    else:
                        template[IMPORTS][i] = import_value['file']
                    if import_value.get('repository', None) is not None:
                        logging.warning("Clouni doesn't support imports \'repository\'")
    template[IMPORTS].extend(default_import_files)
    for i in range(len(template[IMPORTS])):
        template[IMPORTS][i] = os.path.abspath(template[IMPORTS][i])

    copy_of_template = copy.deepcopy(template)
    try:
        tosca_parser_template_object = ToscaTemplate(yaml_dict_tpl=copy_of_template, a_file=a_file)
    except Exception as e:
        logging.exception("Got exception from OpenStack tosca-parser: %s" % e)
        raise Exception("Got exception from OpenStack tosca-parser: %s" % e)

    # After validation, all templates are imported
    if validate_only:
        msg = 'The input "%(template_file)s" successfully passed validation.' \
              % {'template_file': template_file if a_file else 'TOSCA template'}
        return msg, extra

    map_files = config.get_section(config.MAIN_SECTION).get(TOSCA_ELEMENTS_MAP_FILE)
    if isinstance(map_files, six.string_types):
        map_files = [ map_files ]
    default_map_files = []
    for map_file in map_files:
        default_map_files.append(os.path.join(utils.get_project_root_path(), map_file))
    logging.info("Default TOSCA template map file to be used \'%s\'" % json.dumps(default_map_files))

    # Parse and generate new TOSCA service template with only provider specific TOSCA types from normative types
    tosca = ProviderToscaTemplate(template, tosca_parser_template_object, provider, configuration_tool, cluster_name,
                                  host_ip_parameter, public_key_path, is_delete, common_map_files=default_map_files,
                                  grpc_cotea_endpoint=grpc_cotea_endpoint)
    if not extra:
        extra = {}
    return tosca.dict_tpl, utils.deep_update_dict(extra, tosca.extra_configuration_tool_params.get(configuration_tool, {}))
