from vqa import parse_dirty_json

TESTS = [
    ('{"a": 1}', {"a": 1}),
    ('```json\n{"a": 1}\n```', {"a": 1}),
    ('something before ```json\n{"b": [1,2]}\n``` after', {"b": [1, 2]}),
    ('not json at all', 'not json at all'),
    ('42', '42'),
    (['already', 'list'], ['already', 'list']),
    (
        ''' 
        [
        {
                "startTime": "00:23,
                "endTime": "02:31"
        },
        {
                "startTime": "02:38,
                "endTime": "04:13"
        },
        {
                "startTime": "04:20,
                "endTime": "06:37"
        },
        {
                "startTime": "06:43,
                "endTime": "08:17"
        },
        {
                "startTime": "08:25,
                "endTime": "10:33"
        },
        {
                "startTime": "10:45,
                "endTime": "12:26"
        }
]
''', 
        ['already', 'list']
    ),
]


def main():
    ret = 0
    for i, (inp, expected) in enumerate(TESTS):
        out = parse_dirty_json(inp)
        ok = out == expected
        print(f'{"PASS" if ok else "FAIL"} test {i + 1}: {repr(inp)[:50]}')
        if not ok:
            print(f'  expected: {expected}')
            print(f'  got:      {out}')
            ret = 1
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
