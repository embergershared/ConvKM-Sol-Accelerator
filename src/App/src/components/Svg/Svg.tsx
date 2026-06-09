import { Avatar } from "@fluentui/react-components";

export const AppLogo = () => {
  return (
    <Avatar
      image={{
        src: "/sc-logo.png"
      }}
      name="App Logo"
      shape="square"
      size={56}
      aria-label="App Logo"
      style={{
        width: "35px",
        height: "35px",
      }}
    />
  );
};
