from openai import OpenAI
import requests
import typer
from PIL import Image
from cryptography.fernet import Fernet
import os

app = typer.Typer()

OPENAI_API_KEY = "YOUR_API_KEY"


# Generate a key for encryption and save it securely
def generate_key():
    key = Fernet.generate_key()
    with open("secret.key", "wb") as key_file:
        key_file.write(key)


# Load the saved key
def load_key():
    return open("secret.key", "rb").read()


# Encrypt the password or file content
def encrypt_data(data, key):
    fernet = Fernet(key)
    return fernet.encrypt(data.encode())


# Decrypt the password or file content
def decrypt_data(encrypted_data, key):
    fernet = Fernet(key)
    return fernet.decrypt(encrypted_data).decode()


# Encode data into an image using steganography
def encode_data_to_image(image_path, data, output_path):
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        encoded_img = img.copy()
        data += "END"  # Marker to signify the end of data

        data_bits = "".join(
            [format(ord(i), "08b") for i in data]
        )  # Convert data to binary
        data_index = 0

        for y in range(img.height):
            for x in range(img.width):
                r, g, b = img.getpixel((x, y))

                if data_index < len(data_bits):
                    r = (r & 0xFE) | int(data_bits[data_index])  # Modify LSB of red
                    data_index += 1
                if data_index < len(data_bits):
                    g = (g & 0xFE) | int(data_bits[data_index])  # Modify LSB of green
                    data_index += 1
                if data_index < len(data_bits):
                    b = (b & 0xFE) | int(data_bits[data_index])  # Modify LSB of blue
                    data_index += 1

                encoded_img.putpixel((x, y), (r, g, b))

                if data_index >= len(data_bits):
                    break
            if data_index >= len(data_bits):
                break

        encoded_img.save(output_path)
        typer.echo(f"Data encoded in {output_path}")


# Decode data from an image
def decode_data_from_image(image_path):
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        data_bits = ""

        for y in range(img.height):
            for x in range(img.width):
                r, g, b = img.getpixel((x, y))
                data_bits += str(r & 1)  # Extract LSB of red
                data_bits += str(g & 1)  # Extract LSB of green
                data_bits += str(b & 1)  # Extract LSB of blue

        # Split data into 8-bit chunks and convert to characters
        data_bytes = [data_bits[i : i + 8] for i in range(0, len(data_bits), 8)]
        decoded_data = "".join([chr(int(byte, 2)) for byte in data_bytes])

        end_marker = decoded_data.find("END")
        return decoded_data[:end_marker] if end_marker != -1 else None


@app.command()
def save_password(
    image_path: str, password_or_filepath: str, output_path: str = "encoded_image.png"
):
    """
    Encrypt and hide a password or contents of a .txt file within an image.
    - image_path: Path to the image to use for encoding.
    - password_or_filepath: The password text or the path to a .txt file containing data to be hidden.
    - output_path: Optional path to save the encoded image.
    """
    # Load or generate encryption key
    if not os.path.exists("secret.key"):
        generate_key()
    key = load_key()

    # Check if the input is a file path or just a password string
    if os.path.isfile(password_or_filepath):
        with open(password_or_filepath, "r") as file:
            data = file.read()
    else:
        # Use the input directly as a password
        data = password_or_filepath

    # Encrypt the data
    encrypted_data = encrypt_data(data, key).decode()

    # Encode the encrypted data into the image
    encode_data_to_image(image_path, encrypted_data, output_path)
    typer.secho(
        f"Data encrypted and hidden in the image successfully! Saved as {output_path}",
        fg=typer.colors.GREEN,
    )


@app.command()
def retrieve_password(image_path: str, output_file: str = None):
    """
    Retrieve and decrypt a password or file content from an image.
    - image_path: Path to the image containing hidden data.
    - output_file: Optional path to save the retrieved data if it's lengthy.
    """
    # Load the saved key
    key = load_key()

    # Decode the hidden data from the image
    encrypted_data = decode_data_from_image(image_path)
    if encrypted_data is None:
        typer.secho("No encoded data found in the image.", fg=typer.colors.RED)
        return

    # Decrypt the data
    decrypted_data = decrypt_data(encrypted_data.encode(), key)

    # Output data to file if specified or data is too long
    if output_file:
        with open(output_file, "w") as file:
            file.write(decrypted_data)
        typer.secho(f"Data retrieved and saved to {output_file}", fg=typer.colors.GREEN)
    elif len(decrypted_data) > 100:
        # Prompt the user if data is lengthy
        typer.secho(
            "Data is too long to display. Use the '--output-file' option to save it.",
            fg=typer.colors.YELLOW,
        )
    else:
        # Display the data if short
        typer.secho(f"Your data is: {decrypted_data}", fg=typer.colors.BLUE)


@app.command()
def generate_encryption_key():
    """Generate a new encryption key and save it securely."""
    generate_key()
    typer.secho(
        "New encryption key generated and saved to 'secret.key'.",
        fg=typer.colors.YELLOW,
    )


# Initialize the custom DALL-E client
client = OpenAI(api_key=OPENAI_API_KEY)


@app.command()
def generate_image(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "standard",
    output_path: str = "generated_image.png",
):
    """
    Generate an image using DALL-E 3 based on the provided prompt.

    - prompt: A text description of the image you want to generate.
    - size: The size of the generated image (e.g., "1024x1024", "1024x1792", "1792x1024").
    - quality: The quality level ("standard" or "hd" for high detail in DALL-E 3).
    - output_path: The file path to save the generated image.
    """

    try:
        # Use the custom client to generate an image ADD YOUR API KEY HERE
        response = client.images.generate(
            model="dall-e-3", prompt=prompt, size=size, quality=quality, n=1
        )

        # Retrieve the URL of the generated image
        image_url = response.data[0].url
        # Download and save the image
        image_response = requests.get(image_url)
        image_response.raise_for_status()

        # Save the image to the specified output path
        with open(output_path, "wb") as file:
            file.write(image_response.content)

        typer.secho(
            f"Image generated and saved as {output_path}", fg=typer.colors.GREEN
        )
    except requests.exceptions.RequestException as e:
        typer.secho(f"Error downloading image: {e}", fg=typer.colors.RED)


if __name__ == "__main__":
    app()
