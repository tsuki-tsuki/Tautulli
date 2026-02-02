    'FIRST_RUN_COMPLETE', 'GET_FILE_SIZES_HOLD', 'GIT_PATH', 'PMS_LOGS_FOLDER',
    'BACKUP_DIR', 'CACHE_DIR', 'EXPORT_DIR', 'LOG_DIR', 'NEWSLETTER_DIR', 'NEWSLETTER_CUSTOM_DIR',
    'HTTP_HOST', 'HTTP_PORT', 'HTTP_ROOT',
    'HTTP_USERNAME', 'HTTP_PASSWORD', 'HTTP_HASH_PASSWORD', 'HTTP_HASHED_PASSWORD',
    'ENABLE_HTTPS', 'HTTPS_CREATE_CERT', 'HTTPS_CERT', 'HTTPS_CERT_CHAIN', 'HTTPS_KEY',
    'PMS_TOKEN', 'JWT_SECRET', 'OIDC_CLIENT_SECRET'
]
_DO_NOT_IMPORT_KEYS_DOCKER = [
]
_DO_NOT_DOWNLOAD_KEYS = [
    'PMS_TOKEN', 'JWT_SECRET', 'OIDC_CLIENT_SECRET'
]

IS_IMPORTING = False
IMPORT_THREAD = None

SETTINGS = [
    'ANON_REDIRECT',
    'API_KEY',
    'BACKUP_DAYS',
    'BACKUP_DIR',
    'BACKUP_INTERVAL',
    'BUFFER_THRESHOLD',
    'BUFFER_WAIT',
    'CACHE_DIR',
    'CHECK_GITHUB_INTERVAL',
    'CLOUDINARY_API_KEY',
    'CLOUDINARY_API_SECRET',
    'CLOUDINARY_CLOUD_NAME',
    'DATE_FORMAT',
    'EXPORT_DIR',
    'GIT_BRANCH',
    'GIT_PATH',
    'GIT_REMOTE',
    'GIT_TOKEN',
    'HOME_LIBRARY_CARDS',
    'HOME_REFRESH_INTERVAL',
    'HOME_SECTIONS',
    'HOME_STATS_CARDS',
    'HTTPS_CERT',
    'HTTPS_CERT_CHAIN',
    'HTTPS_DOMAIN',
    'HTTPS_IP',
    'HTTPS_KEY',
    'HTTP_BASE_URL',
    'HTTP_PASSWORD',
    'HTTP_PORT',
    'HTTP_ROOT',
    'HTTP_USERNAME',
    'IMGUR_CLIENT_ID',
    'LOGGING_IGNORE_INTERVAL',
    'LOG_DIR',
    'MOVIE_WATCHED_PERCENT',
    'MUSIC_WATCHED_PERCENT',
    'NEWSLETTER_AUTH',
    'NEWSLETTER_CUSTOM_DIR',
    'NEWSLETTER_DIR',
    'NEWSLETTER_PASSWORD',
    'NOTIFY_CONCURRENT_THRESHOLD',
    'NOTIFY_CONTINUED_SESSION_THRESHOLD',
    'NOTIFY_RECENTLY_ADDED_DELAY',
    'NOTIFY_REMOTE_ACCESS_THRESHOLD',
    'NOTIFY_SERVER_CONNECTION_THRESHOLD',
    'NOTIFY_UPLOAD_POSTERS',
    'PMS_CLIENT_ID',
    'PMS_IDENTIFIER',
    'PMS_IP',
    'PMS_IS_CLOUD',
    'PMS_IS_REMOTE',
    'PMS_LOGS_FOLDER',
    'PMS_NAME',
    'PMS_PORT',
    'PMS_SSL',
    'PMS_UPDATE_CHANNEL',
    'PMS_UPDATE_CHECK_INTERVAL',
    'PMS_UPDATE_DISTRO',
    'PMS_UPDATE_DISTRO_BUILD',
    'PMS_URL',
    'PMS_VERSION',
    'PMS_WEB_URL',
    'REFRESH_LIBRARIES_INTERVAL',
    'REFRESH_USERS_INTERVAL',
    'SHOW_ADVANCED_SETTINGS',
    'TIME_FORMAT',
    'TV_WATCHED_PERCENT',
    'WATCHED_MARKER'
]

CHECKED_SETTINGS = [
    'ALLOW_GUEST_ACCESS',
    'ANON_REDIRECT_DYNAMIC',
    'API_ENABLED',
    'CACHE_IMAGES',
    'CHECK_GITHUB',
    'ENABLE_HTTPS',
    'GET_FILE_SIZES',
    'GROUP_HISTORY_TABLES',
    'HISTORY_TABLE_ACTIVITY',
    'HTTPS_CREATE_CERT',
    'HTTP_PLEX_ADMIN',
    'HTTP_PROXY',
    'LAUNCH_BROWSER',
    'LAUNCH_STARTUP',
    'LOG_BLACKLIST',
    'LOG_BLACKLIST_USERNAMES',
    'MONITOR_PMS_UPDATES',
    'MUSICBRAINZ_LOOKUP',
    'NEWSLETTER_INLINE_STYLES',
    'NEWSLETTER_SELF_HOSTED',
    'NOTIFY_CONCURRENT_BY_IP',
    'NOTIFY_CONSECUTIVE',
    'NOTIFY_GROUP_RECENTLY_ADDED_GRANDPARENT',
    'NOTIFY_GROUP_RECENTLY_ADDED_PARENT',
    'NOTIFY_NEW_DEVICE_INITIAL_ONLY',
    'NOTIFY_PLEXPY_UPDATE_REPEAT',
    'NOTIFY_RECENTLY_ADDED_UPGRADE',
    'NOTIFY_SERVER_UPDATE_REPEAT',
    'PLEXPY_AUTO_UPDATE',
    'PMS_URL_MANUAL',
    'REFRESH_LIBRARIES_ON_STARTUP',
    'REFRESH_USERS_ON_STARTUP',
    'SYS_TRAY_ICON',
    'THEMOVIEDB_LOOKUP',
    'TVMAZE_LOOKUP',
    'WEEK_START_MONDAY',
]


def set_is_importing(value):
    global IS_IMPORTING
    IS_IMPORTING = value


def set_import_thread(config=None, backup=False):
    global IMPORT_THREAD
    if config:
        if IMPORT_THREAD:
            return
        IMPORT_THREAD = threading.Thread(target=import_tautulli_config,
                                         kwargs={'config': config, 'backup': backup})
    else:
        IMPORT_THREAD = None


def import_tautulli_config(config=None, backup=False):
    if IS_IMPORTING:
        logger.warn("Tautulli Config :: Another Tautulli config is currently being imported. "
                    "Please wait until it is complete before importing another config.")
        return False

    if backup:
        # Make a backup of the current config first
        logger.info("Tautulli Config :: Creating a config backup before importing.")
        if not make_backup():
            logger.error("Tautulli Config :: Failed to import Tautulli config: failed to create config backup")
            return False

    # Create a new Config object with the imported config file
    try:
        imported_config = Config(config, is_import=True)
    except:
        logger.error("Tautulli Config :: Failed to import Tautulli config: error reading imported config file")
        return False

    logger.info("Tautulli Config :: Importing Tautulli config '%s'...", config)
    set_is_importing(True)

    # Remove keys that should not be imported
    for key in _DO_NOT_IMPORT_KEYS:
        delattr(imported_config, key)
    if plexpy.DOCKER or plexpy.SNAP:
        for key in _DO_NOT_IMPORT_KEYS_DOCKER:
            delattr(imported_config, key)

    # Merge the imported config file into the current config file
    plexpy.CONFIG._config.merge(imported_config._config)
    plexpy.CONFIG.write()

    logger.info("Tautulli Config :: Tautulli config import complete.")
    set_import_thread(None)
    set_is_importing(False)

    # Restart to apply changes
    plexpy.SIGNAL = 'restart'


def make_backup(cleanup=False, scheduler=False):
    """ Makes a backup of config file, removes all but the last 5 backups """

    if scheduler:
        backup_file = 'config.backup-{}.sched.ini'.format(helpers.now())
    else:
        backup_file = 'config.backup-{}.ini'.format(helpers.now())
    backup_folder = plexpy.CONFIG.BACKUP_DIR
    backup_file_fp = os.path.join(backup_folder, backup_file)

    # In case the user has deleted it manually
    if not os.path.exists(backup_folder):
        os.makedirs(backup_folder)

    plexpy.CONFIG.write()
    shutil.copyfile(plexpy.CONFIG_FILE, backup_file_fp)

    if cleanup:
        now = time.time()
        # Delete all scheduled backup older than BACKUP_DAYS.
        for root, dirs, files in os.walk(backup_folder):
            ini_files = [os.path.join(root, f) for f in files if f.endswith('.sched.ini')]
            for file_ in ini_files:
                if os.stat(file_).st_mtime < now - plexpy.CONFIG.BACKUP_DAYS * 86400:
                    try:
                        os.remove(file_)
                    except OSError as e:
                        logger.error("Tautulli Config :: Failed to delete %s from the backup folder: %s" % (file_, e))

    if backup_file in os.listdir(backup_folder):
        logger.debug("Tautulli Config :: Successfully backed up %s to %s" % (plexpy.CONFIG_FILE, backup_file))
        return True
    else:
        logger.error("Tautulli Config :: Failed to backup %s to %s" % (plexpy.CONFIG_FILE, backup_file))
        return False


# pylint:disable=R0902
# it might be nice to refactor for fewer instance variables
class Config(object):
    """ Wraps access to particular values in a config file """

    def __init__(self, config_file, is_import=False):
        """ Initialize the config with values from a file """
        self._config_file = config_file
        try:
            self._config = ConfigObj(self._config_file, encoding='utf-8')
        except ParseError as e:
            logger.error("Tautulli Config :: Error reading configuration file: %s", e)
            raise

        for key in _CONFIG_DEFINITIONS:
            self.check_setting(key)
        if not is_import:
            self._upgrade()
            self._blacklist()

    def _blacklist(self):
        """ Add tokens and passwords to blacklisted words in logger """
        blacklist = set()

        for key, subkeys in self._config.items():
            for subkey, value in subkeys.items():
                if isinstance(value, str) and len(value.strip()) > 5 and \
                    subkey.upper() not in _WHITELIST_KEYS and any(bk in subkey.upper() for bk in _BLACKLIST_KEYS):
                    blacklist.add(value.strip())

        logger._BLACKLIST_WORDS.update(blacklist)

    def _define(self, name):
        key = name.upper()
        ini_key = name.lower()
        definition = _CONFIG_DEFINITIONS[key]
        if len(definition) == 3:
            definition_type, section, default = definition
        else:
            definition_type, section, _, default = definition
        return key, definition_type, section, ini_key, default

    def check_section(self, section):
        """ Check if INI section exists, if not create it """
        if section not in self._config:
            self._config[section] = {}

    def check_setting(self, name):
        """ Check if INI key exists, if not create it """
        key, definition_type, section, ini_key, default = self._define(name)
        self.check_section(section)
        value = self._config[section].get(ini_key, default)
        self._config[section][ini_key] = self._cast_setting(definition_type, value, default)
    
    def get_setting(self, name):
        """ Get the value of a setting, either from the config file or environment variable """
        key, definition_type, section, ini_key, default = self._define(name)
        # Check if the key is in the environment variables
        value = self._from_env(key)
        if not value:
            # If not, check if the key is in the config file
            value = self._config[section].get(ini_key, default)
        return self._cast_setting(definition_type, value, default)
    
    def set_setting(self, name, value):
        """ Set the value of a setting in the config file """
        key, definition_type, section, ini_key, default = self._define(name)
        # Check if the key is in the environment variables
        env_value = self._from_env(key)
        if env_value:
            logger.warn("Tautulli Config :: '%s' set by environment variable. Setting not saved to config.", key)
            return

        # If not, set the value in the config file
        self._config[section][ini_key] = self._cast_setting(definition_type, value, default)
        return self._config[section][ini_key]
    
    def _from_env(self, key):
        """ Get key from environment variables, if it exists """
        env_key = f"TAUTULLI_{key}"
        return os.environ.get(env_key)
    
    def _cast_setting(self, definition_type, value, default=None):
        """ Cast the value to the correct type, or use the default if it fails """
        try:
            return definition_type(value)
        except Exception:
            return definition_type(default)

    def write(self):
        """ Make a copy of the stored config and write it to the configured file """
        new_config = ConfigObj(encoding="UTF-8")
        new_config.filename = self._config_file

        # first copy over everything from the old config, even if it is not
        # correctly defined to keep from losing data
        for key, subkeys in self._config.items():
            if key not in new_config:
                new_config[key] = {}
            for subkey, value in subkeys.items():
                new_config[key][subkey] = value

        # next make sure that everything we expect to have defined is so
        for key in _CONFIG_DEFINITIONS:
            key, definition_type, section, ini_key, default = self._define(key)
            self.check_setting(key)
            if section not in new_config:
                new_config[section] = {}
            new_config[section][ini_key] = self._config[section][ini_key]

        # Write it to file
        logger.info("Tautulli Config :: Writing configuration to file")

        try:
            new_config.write()
        except IOError as e:
            logger.error("Tautulli Config :: Error writing configuration file: %s", e)

        self._blacklist()

    def __getattr__(self, name):
        """
        Returns something from the ini unless it is a real property
        of the configuration object or is not all caps.
        """
        if not re.match(r'[A-Z0-9_]+$', name):
            return super(Config, self).__getattr__(name)
        else:
            return self.get_setting(name)

    def __setattr__(self, name, value):
        """
        Maps all-caps properties to ini values unless they exist on the
        configuration object.
        """
        if not re.match(r'[A-Z_]+$', name):
            super(Config, self).__setattr__(name, value)
            return value
        else:
            return self.set_setting(name, value)

    def __delattr__(self, name):
        """
        Deletes a key from the configuration object.
        """
        if not re.match(r'[A-Z_]+$', name):
            return super(Config, self).__delattr__(name)
        else:
            key, definition_type, section, ini_key, default = self._define(name)
            del self._config[section][ini_key]

    def process_kwargs(self, kwargs):
        """
        Given a big bunch of key value pairs, apply them to the ini.
        """
        for name, value in kwargs.items():
            self.__setattr__(name.upper(), value)

    def _upgrade(self):
        """
        Upgrades config file from previous versions and bumps up config version
        """
        if self.CONFIG_VERSION == 0:
            self.CONFIG_VERSION = 1

        if self.CONFIG_VERSION == 1:
            # Change home_stats_cards to list
            if self.HOME_STATS_CARDS:
                home_stats_cards = ''.join(self.HOME_STATS_CARDS).split(', ')
                if 'watch_statistics' in home_stats_cards:
                    home_stats_cards.remove('watch_statistics')
                    self.HOME_STATS_CARDS = home_stats_cards
            # Change home_library_cards to list
            if self.HOME_LIBRARY_CARDS:
                home_library_cards = ''.join(self.HOME_LIBRARY_CARDS).split(', ')
                if 'library_statistics' in home_library_cards:
                    home_library_cards.remove('library_statistics')
                    self.HOME_LIBRARY_CARDS = home_library_cards

            self.CONFIG_VERSION = 2

        if self.CONFIG_VERSION == 2:
            self.CONFIG_VERSION = 3

        if self.CONFIG_VERSION == 3:
            if self.HTTP_ROOT == '/':
                self.HTTP_ROOT = ''

            self.CONFIG_VERSION = 4

        if self.CONFIG_VERSION == 4:

            self.CONFIG_VERSION = 5

        if self.CONFIG_VERSION == 5:
            self.MONITOR_PMS_UPDATES = 0

            self.CONFIG_VERSION = 6

        if self.CONFIG_VERSION == 6:
            if self.GIT_USER.lower() == 'drzoidberg33':
                self.GIT_USER = 'JonnyWong16'

            self.CONFIG_VERSION = 7

        if self.CONFIG_VERSION == 7:
            self.CONFIG_VERSION = 8

        if self.CONFIG_VERSION == 8:
            self.CONFIG_VERSION = 9

        if self.CONFIG_VERSION == 9:
            if self.PMS_UPDATE_CHANNEL == 'plexpass':
                self.PMS_UPDATE_CHANNEL = 'beta'

            self.CONFIG_VERSION = 10

        if self.CONFIG_VERSION == 10:
            self.GIT_USER = 'Tautulli'
            self.GIT_REPO = 'Tautulli'

            self.CONFIG_VERSION = 11

        if self.CONFIG_VERSION == 11:
            self.ANON_REDIRECT = self.ANON_REDIRECT.replace('http://www.nullrefer.com/?',
                                                            'https://www.nullrefer.com/?')
            self.CONFIG_VERSION = 12

        if self.CONFIG_VERSION == 12:
            self.BUFFER_THRESHOLD = max(self.BUFFER_THRESHOLD, 10)

            self.CONFIG_VERSION = 13

        if self.CONFIG_VERSION == 13:
            self.CONFIG_VERSION = 14

        if self.CONFIG_VERSION == 14:
            if plexpy.DOCKER:
                self.PLEXPY_AUTO_UPDATE = 0

            self.CONFIG_VERSION = 15

        if self.CONFIG_VERSION == 15:
            if self.HTTP_ROOT and self.HTTP_ROOT != '/':
                self.JWT_UPDATE_SECRET = True

            self.CONFIG_VERSION = 16

        if self.CONFIG_VERSION == 16:
            if plexpy.SNAP:
                self.PLEXPY_AUTO_UPDATE = 0

            self.CONFIG_VERSION = 17

        if self.CONFIG_VERSION == 17:
            home_stats_cards = self.HOME_STATS_CARDS
            if 'top_users' in home_stats_cards:
                top_users_index = home_stats_cards.index('top_users')
                home_stats_cards.insert(top_users_index, 'top_libraries')
            else:
                home_stats_cards.append('top_libraries')
            self.HOME_STATS_CARDS = home_stats_cards

            self.CONFIG_VERSION = 18

        if self.CONFIG_VERSION == 18:
            if self.CHECK_GITHUB_INTERVAL > 24:
                self.CHECK_GITHUB_INTERVAL = (
                        int(self.CHECK_GITHUB_INTERVAL // 60)
                        + (self.CHECK_GITHUB_INTERVAL % 60 > 0)
                )

            self.CONFIG_VERSION = 19

        if self.CONFIG_VERSION == 19:
            if self.HTTP_PASSWORD and not self.HTTP_HASHED_PASSWORD:
                self.HTTP_PASSWORD = make_hash(self.HTTP_PASSWORD)
            self.HTTP_HASH_PASSWORD = 1
            self.HTTP_HASHED_PASSWORD = 1

            self.CONFIG_VERSION = 20

        if self.CONFIG_VERSION == 20:
            if self.PMS_UUID:
                self.FIRST_RUN_COMPLETE = 1

            self.CONFIG_VERSION = 21

        if self.CONFIG_VERSION == 21:
            if not self.ANON_REDIRECT_DYNAMIC and not self.ANON_REDIRECT:
                self.ANON_REDIRECT_DYNAMIC = 1

            self.CONFIG_VERSION = 22
