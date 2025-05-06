import os
import git
import logging
from .base import HistorySyncStrategy
from .decorators import retry
from config import Config

class GitHistorySyncStrategy(HistorySyncStrategy):
    """Реализация синхронизации через git"""
    
    def __init__(self, config: Config):
        self.config = config
        self.git_repo_path = config.get_path(config.paths.git_repo)
        logging.info(f"Инициализация GitHistorySyncStrategy с путем репозитория: {self.git_repo_path}")
        self.history_file = os.path.join(self.git_repo_path, 'history.txt')
        
        self._setup_repository_directory()
        self._setup_history_file()
        self._setup_git_repository()
        self._setup_remote_repository()
        self._setup_branch()
        self._configure_merge_strategy()

    def _setup_repository_directory(self):
        """Создает директорию для Git-репозитория, если её нет"""
        logging.info(f"Проверка директории репозитория: {self.git_repo_path}")
        
        # Создаем все родительские директории
        try:
            os.makedirs(self.git_repo_path, exist_ok=True)
            logging.info(f"Директория создана: {self.git_repo_path}")
        except Exception as e:
            logging.error(f"Ошибка при создании директории {self.git_repo_path}: {e}")
            raise
        
        # Проверяем, что директория существует и доступна для записи
        if not os.access(self.git_repo_path, os.W_OK):
            error_msg = f"Нет прав на запись в директорию {self.git_repo_path}"
            logging.error(error_msg)
            raise PermissionError(error_msg)
        
        logging.info(f"Директория {self.git_repo_path} доступна для записи")

    def _setup_history_file(self):
        """Настраивает файл истории"""
        local_history_path = self.config.get_path(self.config.paths.local_history)
        history_file = os.path.join(self.git_repo_path, 'history.txt')
        
        # Если файл существует и является символической ссылкой, удаляем его
        if os.path.exists(history_file) and os.path.islink(history_file):
            os.remove(history_file)
        
        # Если локальный файл истории существует, копируем его содержимое
        if os.path.exists(local_history_path):
            content = self._read_file_with_fallback(local_history_path)
            self._write_file_safely(history_file, content)
        else:
            # Создаем пустой файл, если локальной истории нет
            open(history_file, 'wb').close()

    def _read_file_with_fallback(self, file_path: str) -> list:
        """Читает файл с использованием различных кодировок"""
        encodings = ['utf-8', 'latin-1', 'cp1252']
        content = []
        
        for encoding in encodings:
            try:
                with open(file_path, 'rb') as f:
                    raw_content = f.read()
                content = raw_content.decode(encoding).splitlines(keepends=True)
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logging.error(f"Ошибка при чтении файла {file_path}: {e}")
                break
        
        return content

    def _write_file_safely(self, file_path: str, content: list):
        """Безопасно записывает содержимое в файл"""
        try:
            # Преобразуем содержимое в строку и заменяем проблемные символы
            text_content = ''.join(content)
            # Заменяем проблемные символы на их ASCII эквиваленты или пропускаем их
            clean_content = text_content.encode('ascii', 'ignore').decode('ascii')
            
            # Записываем очищенный текст в файл
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(clean_content)
        except Exception as e:
            logging.error(f"Ошибка при записи файла {file_path}: {e}")

    def _setup_git_repository(self):
        """Настраивает Git-репозиторий"""
        try:
            if self.config.git.repository_url:
                # Проверяем существование директории
                if os.path.exists(self.git_repo_path):
                    try:
                        # Проверяем, является ли директория Git репозиторием
                        self.repo = git.Repo(self.git_repo_path)
                        logging.info(f"Найден существующий репозиторий. Статус:\n{self.repo.git.status()}")
                        
                        # Проверяем состояние репозитория
                        try:
                            # Проверяем наличие несохраненных изменений
                            if self.repo.is_dirty():
                                logging.warning("Обнаружены несохраненные изменения в репозитории")
                                raise git.exc.GitCommandError("dirty", 1, "Repository is dirty")
                            
                            # Проверяем наличие конфликтов
                            if self.repo.index.unmerged_blobs():
                                logging.warning("Обнаружены неразрешенные конфликты в репозитории")
                                raise git.exc.GitCommandError("conflict", 1, "Repository has conflicts")
                            
                            # Проверяем связь с удаленным репозиторием
                            if self.config.git.remote_name not in [remote.name for remote in self.repo.remotes]:
                                logging.warning("Удаленный репозиторий не настроен")
                                raise git.exc.GitCommandError("remote", 1, "Remote not configured")
                            
                            # Пытаемся получить изменения
                            remote = self.repo.remote(self.config.git.remote_name)
                            remote.fetch()
                            logging.info(f"Репозиторий в порядке. Статус:\n{self.repo.git.status()}")
                            
                        except git.exc.GitCommandError as e:
                            logging.warning(f"Проблемы с репозиторием: {e}")
                            # Удаляем проблемный репозиторий
                            logging.info(f"Удаляем проблемный репозиторий в {self.git_repo_path}")
                            import shutil
                            shutil.rmtree(self.git_repo_path)
                            # Создаем новую директорию
                            os.makedirs(self.git_repo_path)
                            # Клонируем заново
                            self.repo = git.Repo.clone_from(
                                self.config.git.repository_url,
                                self.git_repo_path,
                                branch=self.config.git.branch
                            )
                            logging.info(f"Репозиторий успешно пересоздан. Статус:\n{self.repo.git.status()}")
                            
                    except git.exc.InvalidGitRepositoryError:
                        # Если директория существует, но не является Git репозиторием
                        logging.warning(f"Директория {self.git_repo_path} существует, но не является Git репозиторием")
                        # Удаляем директорию
                        import shutil
                        shutil.rmtree(self.git_repo_path)
                        # Создаем новую директорию
                        os.makedirs(self.git_repo_path)
                        # Клонируем
                        self.repo = git.Repo.clone_from(
                            self.config.git.repository_url,
                            self.git_repo_path,
                            branch=self.config.git.branch
                        )
                        logging.info(f"Репозиторий успешно создан. Статус:\n{self.repo.git.status()}")
                else:
                    # Если директории нет, создаем её и клонируем
                    os.makedirs(self.git_repo_path)
                    self.repo = git.Repo.clone_from(
                        self.config.git.repository_url,
                        self.git_repo_path,
                        branch=self.config.git.branch
                    )
                    logging.info(f"Репозиторий успешно клонирован. Статус:\n{self.repo.git.status()}")
            else:
                # Если URL не указан, открываем существующий или создаем новый
                try:
                    self.repo = git.Repo(self.git_repo_path)
                    logging.info(f"Открыт существующий репозиторий. Статус:\n{self.repo.git.status()}")
                except git.exc.InvalidGitRepositoryError:
                    # Создаем новый репозиторий только если не указан URL
                    self.repo = git.Repo.init(self.git_repo_path)
                    logging.info(f"Создан новый Git репозиторий. Статус:\n{self.repo.git.status()}")
                    
                    # Создаем начальный коммит
                    self.repo.index.add(['history.txt'])
                    self.repo.index.commit("Initial commit")
                    logging.info(f"Создан начальный коммит. Статус:\n{self.repo.git.status()}")
        except Exception as e:
            logging.error(f"Ошибка при настройке Git репозитория: {e}")
            raise

    def _setup_remote_repository(self):
        """Настраивает удаленный репозиторий"""
        if self.config.git.repository_url and self.config.git.repository_url not in [remote.url for remote in self.repo.remotes]:
            self._add_remote_repository()

    def _add_remote_repository(self):
        """Добавляет и настраивает удаленный репозиторий"""
        remote = self.repo.create_remote(self.config.git.remote_name, self.config.git.repository_url)
        try:
            self._sync_with_remote(remote)
        except git.exc.GitCommandError:
            self._handle_remote_error(remote)

    def _sync_with_remote(self, remote):
        """Синхронизирует с удаленным репозиторием"""
        remote.fetch()
        if f"{self.config.git.remote_name}/main" in [ref.name for ref in remote.refs]:
            self._setup_tracking_branch(remote)
        else:
            self._push_local_branch(remote)

    def _setup_tracking_branch(self, remote):
        """Настраивает отслеживание ветки"""
        if 'main' not in self.repo.heads:
            self.repo.create_head('main', remote.refs.main)
        self.repo.heads.main.set_tracking_branch(remote.refs.main)
        self.repo.heads.main.checkout()

    def _push_local_branch(self, remote):
        """Отправляет локальную ветку в удаленный репозиторий"""
        if 'main' not in self.repo.heads:
            self.repo.create_head('main', self.initial_commit)
        self.repo.heads.main.checkout()
        remote.push('main', set_upstream=True)

    def _handle_remote_error(self, remote):
        """Обрабатывает ошибки при работе с удаленным репозиторием"""
        if 'main' not in self.repo.heads:
            self.repo.create_head('main', self.initial_commit)
        self.repo.heads.main.checkout()
        remote.push('main', set_upstream=True)

    def _setup_branch(self):
        """Настраивает рабочую ветку"""
        self.branch = self.config.git.branch
        if self.branch != 'main':
            self._setup_custom_branch()

    def _setup_custom_branch(self):
        """Настраивает пользовательскую ветку"""
        if self.branch not in self.repo.heads:
            self.repo.create_head(self.branch, self.repo.heads.main.commit)
        self.repo.heads[self.branch].checkout()

    def _configure_merge_strategy(self):
        """Настраивает стратегию слияния"""
        with self.repo.config_writer() as config_writer:
            config_writer.set_value("pull", "rebase", "false")

    def merge_histories(self, current_history: list, remote_history: list) -> list:
        """Объединяет две истории, удаляя дубликаты и сортируя по временным меткам"""
        merged_history = list(set(current_history + remote_history))
        merged_history.sort()  # Сортируем по временным меткам
        return merged_history

    def get_current_history(self) -> list:
        """Получает текущую версию истории из файла"""
        if os.path.exists(self.history_file):
            return self._read_file_with_fallback(self.history_file)
        return []

    def get_remote_history(self) -> list:
        """Получает историю из удаленной ветки"""
        try:
            self.repo.git.fetch()
            remote_content = self.repo.git.show(f'origin/{self.branch}:{os.path.basename(self.history_file)}')
            return remote_content.splitlines(keepends=True)
        except git.exc.GitCommandError:
            return []

    def save_history(self, history: list):
        """Сохраняет историю в файл"""
        self._write_file_safely(self.history_file, history)

    def _try_pull(self, remote) -> bool:
        """Пытается выполнить pull с обработкой конфликтов"""
        try:
            if not self._fetch_remote(remote):
                return True
            
            if not self._check_remote_branch(remote):
                return True
            
            return self._perform_pull(remote)
        except git.exc.GitCommandError as e:
            if "conflict" in str(e).lower():
                logging.info("Обнаружен конфликт, выполняем разрешение...")
                self._resolve_conflict()
                return False
            raise

    def _fetch_remote(self, remote) -> bool:
        """Пытается получить изменения из удаленного репозитория"""
        try:
            remote.fetch()
            return True
        except git.exc.GitCommandError as e:
            if "couldn't find remote ref" in str(e) or "does not appear to be a git repository" in str(e):
                return False
            raise

    def _check_remote_branch(self, remote) -> bool:
        """Проверяет наличие удаленной ветки"""
        try:
            remote.refs[self.branch]
            return True
        except (IndexError, AttributeError):
            return False

    def _perform_pull(self, remote) -> bool:
        """Выполняет pull с разрешением несвязанных историй"""
        try:
            self.repo.git.pull('--no-rebase', '--allow-unrelated-histories', remote.name, self.branch)
            return True
        except git.exc.GitCommandError as e:
            if "conflict" in str(e).lower():
                logging.info("Обнаружен конфликт, выполняем разрешение...")
                self._resolve_conflict()
                return False
            raise

    def _try_push(self, remote) -> bool:
        """Пытается выполнить push"""
        try:
            # 1. Очищаем репозиторий
            self.repo.git.reset('--hard')
            self.repo.git.clean('-fd')
            
            # 2. Получаем локальную историю
            local_history = self._read_file_with_fallback(self.config.get_path(self.config.paths.local_history))
            
            # 3. Сохраняем локальную историю
            self.save_history(local_history)
            self.repo.index.add(['history.txt'])
            self.repo.index.commit("Local history")
            
            # 4. Пытаемся выполнить pull с флагом --allow-unrelated-histories
            self.repo.git.pull('--no-rebase', '--allow-unrelated-histories', remote.name, self.branch)
            
            # 5. Получаем текущую историю после pull
            current_history = self.get_current_history()
            
            # 6. Мержим истории
            merged_history = self.merge_histories(local_history, current_history)
            self.save_history(merged_history)
            self.repo.index.add(['history.txt'])
            self.repo.index.commit("Merged history")
            
            # 7. Пытаемся выполнить push
            remote.push(self.branch)
            return True
        except git.exc.GitCommandError as e:
            if "refusing to merge unrelated histories" in str(e).lower():
                logging.warning("Обнаружены несвязанные истории, выполняем принудительное объединение...")
                # Выполняем pull с флагом --allow-unrelated-histories
                self.repo.git.pull('--no-rebase', '--allow-unrelated-histories', remote.name, self.branch)
                # Повторяем операцию
                return self._try_push(remote)
            elif "conflict" in str(e).lower():
                logging.warning("Обнаружен конфликт, выполняем hard reset и повторяем...")
                # Выполняем hard reset
                self.repo.git.reset('--hard')
                # Повторяем операцию
                return self._try_push(remote)
            elif "permission denied" in str(e).lower():
                logging.error("Отказано в доступе к удаленному репозиторию. Проверьте настройки доступа.")
                raise
            else:
                logging.error(f"Ошибка при отправке изменений: {e}")
                raise

    def _resolve_conflict(self):
        """Разрешает конфликт при синхронизации"""
        logging.info("Разрешение конфликта...")
        
        # Выполняем hard reset
        self.repo.git.reset('--hard')
        
        # Получаем текущую историю
        current_history = self.get_current_history()
        
        # Получаем локальную историю
        local_history = self._read_file_with_fallback(self.config.get_path(self.config.paths.local_history))
        
        # Объединяем истории
        merged_history = self.merge_histories(local_history, current_history)
        
        # Сохраняем объединенную историю
        self.save_history(merged_history)
        
        # Добавляем файл в индекс
        self.repo.index.add(['history.txt'])
        
        # Фиксируем изменения
        self.repo.index.commit("Resolve merge conflict")
        
        logging.info("Конфликт разрешен")

    @retry(max_attempts=3)
    def read_remote_history(self) -> list:
        """Чтение удаленной истории с синхронизацией с удаленным репозиторием"""
        if not self.config.git.repository_url:
            return self.get_current_history()
        
        try:
            remote = self.repo.remote(self.config.git.remote_name)
            return self._sync_and_read_history(remote)
        except git.exc.GitCommandError as e:
            if "couldn't find remote ref" in str(e):
                return []
            raise

    def _sync_and_read_history(self, remote) -> list:
        """Синхронизирует и читает историю"""
        remote.fetch()
        try:
            self._prepare_for_sync()
            self._perform_sync(remote)
            return self._read_and_merge_histories()
        except git.exc.GitCommandError as e:
            return self._handle_sync_error(e)

    def _prepare_for_sync(self):
        """Подготавливает файлы для синхронизации"""
        if os.path.exists(self.history_file):
            if os.path.islink(self.history_file):
                os.unlink(self.history_file)
            else:
                os.remove(self.history_file)

    def _perform_sync(self, remote):
        """Выполняет синхронизацию"""
        self.repo.git.pull('--no-rebase', '--allow-unrelated-histories', remote.name, self.branch)

    def _read_and_merge_histories(self) -> list:
        """Читает и объединяет истории"""
        local_history = self._read_local_history()
        remote_history = self._read_remote_file()
        return self._merge_and_sort_histories(local_history, remote_history)

    def _read_local_history(self) -> list:
        """Читает локальную историю"""
        if os.path.exists(self.history_file):
            return self._read_file_with_fallback(self.history_file)
        return []

    def _read_remote_file(self) -> list:
        """Читает удаленный файл истории"""
        try:
            remote_content = self.repo.git.show(f'origin/{self.branch}:{os.path.basename(self.history_file)}')
            return remote_content.splitlines(keepends=True)
        except git.exc.GitCommandError:
            return []
        except Exception as e:
            logging.error(f"Ошибка при чтении удаленной истории: {e}")
            return []

    def _merge_and_sort_histories(self, local_history: list, remote_history: list) -> list:
        """Объединяет и сортирует истории"""
        merged_history = list(set(local_history + remote_history))
        merged_history.sort(key=lambda x: int(x.split(':')[1].strip()))
        return merged_history

    def _save_and_link_history(self, history: list):
        """Сохраняет историю в файл"""
        local_history_path = self.config.get_path(self.config.paths.local_history)
        self._write_file_safely(self.history_file, history)
        self._write_file_safely(local_history_path, history)

    def _handle_sync_error(self, error) -> list:
        """Обрабатывает ошибки при синхронизации"""
        if "conflict" in str(error).lower():
            logging.info("Обнаружен конфликт, выполняем разрешение...")
            self._resolve_conflict()
            return self.get_current_history()
        elif "couldn't find remote ref" in str(error):
            logging.warning("Удаленная ветка не найдена, создаем новую...")
            return []
        else:
            logging.error(f"Ошибка при синхронизации: {error}")
            raise

    def write_remote_history(self, new_history: list):
        """Запись удаленной истории с отправкой изменений"""
        current_history = self.get_current_history()
        merged_history = self.merge_histories(current_history, new_history)
        self.save_history(merged_history)

    @retry(max_attempts=3)
    def commit_changes(self, message: str):
        """Сохранение изменений с отправкой в удаленный репозиторий"""
        self._commit_local_changes(message)
        if self.config.git.repository_url:
            self._push_changes()

    def _commit_local_changes(self, message: str):
        """Фиксирует локальные изменения"""
        self.repo.index.add(['history.txt'])
        if self.repo.is_dirty():
            self.repo.index.commit(message)

    def _push_changes(self):
        """Отправляет изменения в удаленный репозиторий"""
        remote = self.repo.remote(self.config.git.remote_name)
        self._try_push(remote)

    @retry(max_attempts=3)
    def clear_remote_history(self):
        """Очищает удаленную историю"""
        try:
            # Очищаем локальную историю
            self._clear_local_history()
            
            # Создаем пустой файл истории
            self.save_history([])
            
            # Добавляем файл в индекс
            self.repo.index.add(['history.txt'])
            
            # Фиксируем изменения
            self.repo.index.commit("Clear remote history")
            
            # Отправляем изменения в удаленный репозиторий
            if self.config.git.repository_url:
                remote = self.repo.remote(self.config.git.remote_name)
                try:
                    # Пытаемся отправить изменения
                    remote.push(self.branch, force=True)
                    logging.info("Удаленная история успешно очищена")
                    return True
                except git.exc.GitCommandError as e:
                    if "rejected" in str(e).lower():
                        # Если изменения отклонены, пробуем принудительно
                        logging.warning("Изменения отклонены, пробуем принудительно...")
                        remote.push(self.branch, force=True)
                        logging.info("Удаленная история успешно очищена (принудительно)")
                        return True
                    else:
                        logging.error(f"Ошибка при отправке изменений: {e}")
                        return False
            return True
        except Exception as e:
            logging.error(f"Ошибка при очистке удаленной истории: {e}")
            return False

    def _clear_local_history(self):
        """Очищает локальную историю"""
        self.save_history([])

    def _commit_clear_history(self):
        """Фиксирует очистку истории"""
        self.repo.index.add([self.history_file])
        self.repo.index.commit("Clear remote history")

    def _push_clear_history(self) -> bool:
        """Отправляет очищенную историю в удаленный репозиторий"""
        if not self.config.git.repository_url:
            return True
        
        remote = self.repo.remote(self.config.git.remote_name)
        if not self._try_push(remote):
            logging.warning("Не удалось отправить изменения. Попробуйте выполнить pull и повторить операцию.")
            return False
        return True 