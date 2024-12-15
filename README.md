
### Steps for Setting Up Google Maps API:

1. **Create a Google Cloud Account**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - If you don’t already have a Google Cloud account, you’ll need to create one. Follow the instructions on the site to create an account.

2. **Create a New Project**:
   - Once logged in, click on the project dropdown (top left), then click **New Project**.
   - Name your project (e.g., *PetAppMap*), and click **Create**.

3. **Enable the Google Maps APIs**:
   - In the Google Cloud Console, go to **APIs & Services > Library**.
   - Search for and enable the following APIs:
     - **Maps JavaScript API**: Allows embedding the map on your site.
     - **Places API**: Allows you to use places search and location data.
   - Click **Enable** for both APIs.

4. **Create API Key**:
   - After enabling the APIs, go to **APIs & Services > Credentials**.
   - Click **Create Credentials** and select **API Key**.
   - Google will generate an API key for you. Copy this key.

5. **Add the API Key to Your Project**:
   - In your project directory, create a file called `.env` at the root of the project.
   - Add the following line to the `.env` file:
     ```env
     GOOGLE_API_KEY=YOUR_API_KEY_HERE
     ```
     Replace `YOUR_API_KEY_HERE` with the API key you copied from the Google Cloud Console.

6. **Install Required Dependencies**:
   - Ensure you have the necessary libraries installed. Run the following command to install any missing dependencies:
     ```bash
     pip install python-dotenv
     ```

7. **Ensure .env Is Added to `.gitignore`**:
   - Check that the `.env` file is listed in the `.gitignore` to keep your API key private. If not, add the following line to your `.gitignore`:
     ```
     .env
     ```
