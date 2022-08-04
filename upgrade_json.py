import os
import sys
import json

BASE_DIR = os.getcwd()


def get_img_path(code, base_dir):
    extensions = ["jpg", "jpeg", "png"]
    for extension in extensions:
        if os.path.exists(os.path.join(BASE_DIR, f'src/img/{base_dir}/{code}.{extension}')):
            return f"/media/images/commands/{base_dir}/{code}.{extension}"


def start_upgrade(filename):
    with open(filename, "r") as json_data:
        data = json.load(json_data)

    basename = os.path.basename(filename).split('.')[0]
    for item in data.get(basename):
        item["image"] = get_img_path(item["code"], "grupos")
        for sub_item in item["products"]:
            sub_item["image"] = get_img_path(sub_item["code"], "produtos")

    dumps = json.dumps(data, indent=4, sort_keys=True)
    with open(filename, 'w') as json_data:
        json_data.write(dumps)


if __name__ == "__main__":
    args = sys.argv
    filename = args[1 if len(args) > 1 else exit()]
    start_upgrade(filename)
