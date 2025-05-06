from functools import wraps
from typing import Callable, TypeVar
import logging

T = TypeVar('T')

def retry(max_attempts: int = 3):
    """Декоратор для повторных попыток выполнения операции
    
    Args:
        max_attempts (int): Максимальное количество попыток выполнения операции
        
    Returns:
        Callable: Декорированная функция с логикой повторных попыток
        
    Example:
        @retry(max_attempts=3)
        def some_function():
            # код функции
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            attempt = 0
            while attempt < max_attempts:
                attempt += 1
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        logging.warning(f"Не удалось выполнить операцию после {max_attempts} попыток: {e}")
                        raise
                    logging.warning(f"Попытка {attempt}/{max_attempts} не удалась: {e}")
            raise Exception(f"Достигнуто максимальное количество попыток ({max_attempts})")
        return wrapper
    return decorator 