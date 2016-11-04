def mean(numbers):
    return sum(numbers) / len(numbers)


def median(numbers):
    return percentile(numbers, 50)


def percentile(numbers, percentage):
    numbers = sorted(numbers)
    count = len(numbers)
    
    idx = count * percentage / 100
    idx = int(idx)
    
    return numbers[idx]
